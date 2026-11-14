"""Local dashboard and sanitized monitor endpoints; no provider calls here."""
import re
import time
import uuid
import sys
from pathlib import Path
from fastapi import Request, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from aura.observability.events import EventBus, current_bus, current_trace, emit


def install_dashboard(app):
    app.state.telemetry = EventBus()
    assets = Path(__file__).resolve().parents[3] / 'frontend'
    if not assets.is_dir():
        assets = Path(sys.prefix) / 'share/aura/frontend'
    if assets.is_dir():
        app.mount('/assets', StaticFiles(directory=assets), name='frontend')
        @app.get('/', include_in_schema=False)
        async def index():
            return FileResponse(assets / 'index.html')

    @app.middleware('http')
    async def monitor(request, call_next):
        path = request.url.path
        quiet = request.method=='GET' and (path=='/' or path.startswith(('/assets','/monitor','/workflows','/documents','/providers','/rag/status','/nlp/status','/health')))
        trace = request.headers.get('x-aura-trace','')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',trace): trace=uuid.uuid4().hex
        bus_token=current_bus.set(app.state.telemetry)
        trace_token=current_trace.set(trace)
        started=time.monotonic()
        try:
            # Use route patterns where available; never log query strings or bodies.
            if not quiet: emit('server_request','started',method=request.method, endpoint=path[:160])
            response=await call_next(request)
            if not quiet: emit('server_request','completed' if response.status_code<400 else 'failed',
                               method=request.method,endpoint=path[:160],http_status=response.status_code,
                               duration_ms=round((time.monotonic()-started)*1000,2))
            response.headers['x-aura-trace']=trace
            return response
        finally:
            current_trace.reset(trace_token);current_bus.reset(bus_token)

    @app.get('/monitor/events')
    async def events(after: int=Query(0,ge=0)):
        return app.state.telemetry.read(after)

    @app.get('/monitor/status')
    async def status(request:Request):
        gateway=request.app.state.gateway
        provider,model=gateway.preferred_generation()
        return {'provider':provider,'model':model,'usage_tokens':gateway.usage,
                'cloudflare':gateway.status['cloudflare'].model_dump(),
                'tunnel':{'state':'unverified','detail':'AURA does not manage or inspect cloudflared. Cloudflare AI requests are not a tunnel.'},
                'credits':'unknown','telemetry':'Last 5000 events in this server process; workflow lifecycle is also saved in SQLite.',
                'langgraph':'planning → task_wave (repeat while tasks remain) → verification',
                'langchain':'LangChain-core Document preserves retrieved text and metadata for answer context.'}

    @app.get('/monitor/workflows')
    async def workflows(request:Request,project_id:str):
        memory=request.app.state.memory
        rows=memory.db.execute('SELECT id,state,updated FROM workflows WHERE project=? ORDER BY updated DESC LIMIT 30',(project_id,)).fetchall()
        return [{'id':r[0],'state':r[1],'updated':r[2]} for r in rows]
