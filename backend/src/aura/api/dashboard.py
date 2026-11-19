"""
FILE: backend/src/aura/api/dashboard.py
PURPOSE: Serve dashboard assets and expose sanitized monitoring endpoints.
MAIN RESPONSIBILITY: Dashboard And Monitoring.
INPUTS: FastAPI app, event cursors and project identifiers.
OUTPUTS: HTML/static files, recent events, workflow list and provider status.
IMPORTANT FUNCTIONS / CLASSES: install_dashboard.
CONNECTED MODULES: aura.observability.events.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "The dashboard reads real events; it does not expose hidden model reasoning or an account balance."
"""
# PRESENTATION SECTION: DASHBOARD AND MONITORING
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
    """Purpose: Dashboard connection.
    
    Inputs: FastAPI app.
    Process and rationale: Mount source or installed frontend assets and register trace middleware plus monitor endpoints; make real execution observable.
    Returns: Routes and middleware installed on the supplied app.
    """
    app.state.telemetry = EventBus()
    assets = Path(__file__).resolve().parents[4] / 'frontend'
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
        quiet = request.method=='GET' and (path=='/' or path.startswith(('/assets','/monitor','/workflows','/documents','/providers','/rag/status','/ingestion/jobs','/nlp/status','/health')))
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

    @app.get('/monitor/stream')
    async def stream(request: Request, trace_id: str=Query(pattern=r'^[a-zA-Z0-9_-]{1,80}$'), after:int=Query(0,ge=0)):
        import asyncio
        import json
        from fastapi.responses import StreamingResponse
        try:
            cursor=max(after,int(request.headers.get('last-event-id','0')))
        except ValueError:
            cursor=after
        async def rows():
            nonlocal cursor
            last=time.monotonic()
            while not await request.is_disconnected():
                batch=app.state.telemetry.read(cursor)
                if batch['truncated']:
                    yield 'event: gap\ndata: {}\n\n'
                for row in batch['events']:
                    if row['trace_id']==trace_id:
                        yield f"id: {row['sequence']}\ndata: {json.dumps(row)}\n\n"
                cursor=batch['cursor']
                if time.monotonic()-last>=12:
                    yield ': heartbeat\n\n'
                    last=time.monotonic()
                await asyncio.sleep(0.35)
        return StreamingResponse(rows(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

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
