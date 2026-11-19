"""
FILE: backend/src/aura/api/application.py
PURPOSE: Compose the FastAPI application and manage shared service lifetimes.
MAIN RESPONSIBILITY: Application Startup.
INPUTS: Optional Settings and incoming HTTP requests.
OUTPUTS: FastAPI app with RAG, NLP, workflow and dashboard routes.
IMPORTANT FUNCTIONS / CLASSES: create_app.
CONNECTED MODULES: aura.rag.pipeline, aura.rag.api.routes, aura.nlp.service, aura.nlp.api.routes, aura.orchestration.workflow.engine, aura.orchestration.workflow.persistence, aura.agents.tools.dispatcher, aura.orchestration.api.routes, aura.core, aura.core, aura.llm.gateway, aura.llm.transport.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "The application factory connects our services once and closes their resources at shutdown."
"""
# PRESENTATION SECTION: APPLICATION STARTUP
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path
from aura.rag.pipeline import Pipeline
from aura.rag.api.routes import router
from aura.rag.api.ingestion_jobs import router as ingestion_router
from aura.rag.ingestion.jobs import IngestionQueue
from aura.nlp.service import NLP
from aura.nlp.api.routes import router as nlp_router
from aura.orchestration.workflow.engine import Engine
from aura.orchestration.workflow.persistence import Memory
from aura.agents.tools.dispatcher import Dispatcher
from aura.orchestration.api.routes import router as agent_router
from aura.core import ServiceError
import psutil
from aura.core import Settings, configure_logging
from aura.llm.gateway import Gateway
from aura.llm.transport import Transport

def create_app(settings: Settings | None=None) -> FastAPI:
    """Purpose: Application startup.
    
    Inputs: Optional Settings; otherwise load environment configuration.
    Process and rationale: Compose shared Gateway, Pipeline, NLP, Memory and Engine during lifespan; install routers and dashboard; close owned resources on shutdown.
    Returns: Configured FastAPI application.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging()
        transport=Transport(settings or Settings())
        app.state.gateway=Gateway(settings or Settings(),transport)
        directory=Path(transport.settings.data_dir)
        local_embedding=transport.settings.embedding_provider=='local_minilm'
        if local_embedding:
            # Distinct dimensions require separate indexes, document inventories and recovery queues.
            directory=directory/'local-minilm'
        app.state.rag=Pipeline(app.state.gateway,directory,transport.settings.qdrant_url,local_embedding=local_embedding)
        app.state.nlp=NLP(app.state.rag.embedding, transport.settings.nlp_model, transport.settings.nlp_domain_terms)
        app.state.memory=Memory(directory/'workflows.sqlite')
        app.state.engine=Engine(app.state.gateway,app.state.memory,Dispatcher(app.state.rag,app.state.nlp,directory/'files',app.state.memory))
        app.state.jobs={}
        app.state.ingestion=IngestionQueue(directory,app.state.rag,app.state.telemetry)
        try:
            for provider in app.state.gateway.keys:
                await app.state.gateway.discover(provider)
            app.state.ingestion.start()
            yield
        finally:
            await app.state.ingestion.close()
            await app.state.engine.shutdown()
            app.state.memory.close()
            app.state.rag.close()
            await transport.close()
    app=FastAPI(lifespan=lifespan)
    from .projects import router as project_router
    app.include_router(project_router)
    app.include_router(router)
    app.include_router(ingestion_router)
    app.include_router(nlp_router)
    app.include_router(agent_router)
    @app.exception_handler(ServiceError)
    async def service_error(request,exc):
        code=404 if exc.code.endswith('_not_found') else 429 if exc.code in ('http_429','rate_limited','ingestion_queue_full') else 415 if exc.code=='unsupported_file_type' else 503 if exc.code.startswith(('http_','connection','timeout','ocr_')) else 422
        return JSONResponse(status_code=code,content={'error':exc.code})
    @app.get('/health')
    async def health():
        g=app.state.gateway
        return {'status':'ready' if g.verified else 'unverified','rss_mb':round(psutil.Process().memory_info().rss/1024**2,2),'local_inference':g.settings.aura_llm_provider=='ollama'}
    @app.get('/providers/status')
    async def status(): return app.state.gateway.status
    @app.get('/models')
    async def models():
        g=app.state.gateway
        return {'discovered':g.available,'inference_verified':sorted(g.verified)}
    from .dashboard import install_dashboard
    install_dashboard(app)
    return app
app=create_app()
