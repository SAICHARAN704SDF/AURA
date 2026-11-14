"""Request-local tracing. Never record arguments, prompts, keys, or raw errors."""
import asyncio
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
import threading
import time
import uuid

current_bus = ContextVar('aura_event_bus', default=None)
current_trace = ContextVar('aura_trace', default='')
parent_span = ContextVar('aura_parent_span', default=None)

class EventBus:
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
    bus = current_bus.get()
    if bus:
        bus.publish(dict(trace_id=current_trace.get(), parent_id=parent_span.get(), stage=stage, status=status, **details))

@contextmanager
def span(stage, **details):
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
