"""
FILE: backend/src/aura/observability/events.py
PURPOSE: Correlate bounded telemetry using request-local context and spans.
MAIN RESPONSIBILITY: Live Execution Events.
INPUTS: Stage/status and explicitly supplied safe metadata.
OUTPUTS: Sequenced events with trace IDs, durations and statuses.
IMPORTANT FUNCTIONS / CLASSES: EventBus, emit, span, traced.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: backend/src/aura/llm/gateway.py, backend/src/aura/llm/transport.py, backend/src/aura/memory/manager.py, backend/src/aura/rag/pipeline.py, backend/src/aura/nlp/service.py, backend/src/aura/api/dashboard.py, backend/src/aura/llm/providers/agentrouter.py, backend/src/aura/agents/verification/claims.py, backend/src/aura/rag/ingestion/documents.py, backend/src/aura/rag/ingestion/ocr.py, backend/src/aura/rag/embeddings/cache.py, backend/src/aura/rag/chunking/chunker.py, backend/src/aura/rag/retrieval/retriever.py, backend/src/aura/rag/generation/generator.py, backend/src/aura/rag/generation/context.py, backend/src/aura/nlp/linguistics/processor.py, backend/src/aura/nlp/semantic/similarity.py, backend/src/aura/orchestration/graph/nodes.py, backend/src/aura/orchestration/workflow/engine.py.
PRESENTATION EXPLANATION: "The live graph displays actual events; detailed spans are memory-resident and can expire."
"""
# PRESENTATION SECTION: LIVE EXECUTION EVENTS
import asyncio
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
import os
import json
import logging
import threading
import time
import uuid

current_bus = ContextVar('aura_event_bus', default=None)
current_trace = ContextVar('aura_trace', default='')
parent_span = ContextVar('aura_parent_span', default=None)

class EventBus:
    """Thread-safe bounded in-process event buffer. publish assigns monotonic sequence numbers; read returns events after a cursor and indicates expired history."""
    def __init__(self, capacity=5000):
        self.rows = deque(maxlen=capacity)
        self.sequence = 0
        self.lock = threading.Lock()
    def publish(self, event):
        with self.lock:
            self.sequence += 1
            self.rows.append(dict(event, sequence=self.sequence, time=time.time()))
    def read(self, after=0):
        with self.lock:
            return {'events':[e.copy() for e in self.rows if e['sequence']>after],
                    'cursor':self.sequence, 'truncated':bool(self.rows and after and after<self.rows[0]['sequence']-1)}

def emit(stage, status='info', **details):
    if os.environ.get('RESEARCHOS_JSON_LOGS') == '1':
        # Explicit fields keep source content, credentials and raw provider responses out of logs.
        record = {'stage':stage, 'status':status, 'trace_id':current_trace.get()}
        for key in ('duration_ms','tokens','chunks','http_status','attempt','model','provider'):
            if key in details:
                record[key] = details[key]
        logging.getLogger('researchos.events').info(json.dumps(record,ensure_ascii=True))
    bus = current_bus.get()
    if bus:
        bus.publish(dict(trace_id=current_trace.get(), parent_id=parent_span.get(), stage=stage, status=status, **details))

@contextmanager
def span(stage, **details):
    """Purpose: Execution tracing.
    
    Inputs: Stage and explicitly supplied safe details.
    Process and rationale: Create a timed context, emit start and completion/failure events and restore parent context even on errors.
    Returns: Context manager; original exceptions are re-raised.
    """
    if os.environ.get('RESEARCHOS_OTEL') == '1':
        from opentelemetry import trace
        otel = trace.get_tracer('researchos').start_span(stage)
        otel.set_attribute('researchos.trace_id', current_trace.get())
        context = trace.use_span(otel,end_on_exit=True,record_exception=False,set_status_on_exception=False)
        context.__enter__()
    else:
        context = None
    identifier = uuid.uuid4().hex
    started = time.monotonic()
    emit(stage, 'started', span_id=identifier, **details)
    token = parent_span.set(identifier)
    try:
        yield
    except BaseException as exc:
        emit(stage, 'cancelled' if isinstance(exc,asyncio.CancelledError) else 'failed', span_id=identifier,
             error=getattr(exc,'code',type(exc).__name__), duration_ms=round((time.monotonic()-started)*1000,2))
        raise
    else:
        emit(stage, 'completed', span_id=identifier, duration_ms=round((time.monotonic()-started)*1000,2))
    finally:
        parent_span.reset(token)
        if context is not None:
            context.__exit__(None,None,None)

def traced(stage):
    def decorate(fn):
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def asynchronous(*args, **kwargs):
                with span(stage):
                    return await fn(*args, **kwargs)
            return asynchronous
        @wraps(fn)
        def synchronous(*args, **kwargs):
            with span(stage):
                return fn(*args, **kwargs)
        return synchronous
    return decorate
