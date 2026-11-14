"""Application wiring and API lifecycle; startup probes never run inference."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path
from aura.rag.pipeline import Pipeline
from aura.rag.api.routes import router
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
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging()
        transport=Transport(settings or Settings())
        app.state.gateway=Gateway(settings or Settings(),transport)
        app.state.rag=Pipeline(app.state.gateway,Path(transport.settings.data_dir),transport.settings.qdrant_url)
        app.state.nlp=NLP(app.state.rag.embedding)
        app.state.memory=Memory(Path(transport.settings.data_dir)/'workflows.sqlite')
        app.state.engine=Engine(app.state.gateway,app.state.memory,Dispatcher(app.state.rag,app.state.nlp,Path(transport.settings.data_dir)/'files',app.state.memory))
        app.state.jobs={}
        try:
            for provider in app.state.gateway.keys:
                await app.state.gateway.discover(provider)
            yield
        finally:
            await app.state.engine.shutdown()
            app.state.memory.close()
            app.state.rag.close()
            await transport.close()
    app=FastAPI(lifespan=lifespan)
    app.include_router(router)
    app.include_router(nlp_router)
    app.include_router(agent_router)
    @app.exception_handler(ServiceError)
    async def service_error(request,exc):
        code=404 if exc.code.endswith('_not_found') else 429 if exc.code in ('http_429','rate_limited') else 415 if exc.code=='unsupported_file_type' else 503 if exc.code.startswith(('http_','connection','timeout','ocr_')) else 422
        return JSONResponse(status_code=code,content={'error':exc.code})
    @app.get('/health')
    async def health():
        g=app.state.gateway
        return {'status':'ready' if g.verified else 'unverified','rss_mb':round(psutil.Process().memory_info().rss/1024**2,2),'local_inference':False}
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
