"""
FILE: backend/src/aura/llm/transport.py
PURPOSE: Bound asynchronous HTTP concurrency, retries and process memory use.
MAIN RESPONSIBILITY: Provider Http Transport.
INPUTS: HTTP method, URL and request options.
OUTPUTS: Validated JSON dictionary or sanitized ServiceError.
IMPORTANT FUNCTIONS / CLASSES: Transport.
CONNECTED MODULES: aura.observability.events, aura.core.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py.
PRESENTATION EXPLANATION: "Retries respect a bounded wait budget; they cannot increase provider quota."
"""
# PRESENTATION SECTION: PROVIDER HTTP TRANSPORT
import asyncio
import math
from urllib.parse import urlsplit
from aura.observability.events import emit
import httpx
import psutil
from aura.core import Settings, ServiceError

class Transport:
    """Owned or injected asynchronous HTTP client with bounded concurrency and retries. Provider gateways use request; close releases only an owned client."""
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=settings.timeout, follow_redirects=False)
        self.owned = client is None
        self.limit = asyncio.Semaphore(settings.concurrency)

    async def close(self) -> None:
        if self.owned:
            await self.client.aclose()

    async def request(self, method: str, url: str, **kwargs) -> dict:
        """Purpose: HTTP retries.
        
        Inputs: HTTP method, URL and request keyword arguments.
        Process and rationale: Apply memory/concurrency guards and bounded retries; validate JSON and raise safe errors instead of raw provider bodies.
        Returns: JSON dictionary.
        """
        if psutil.Process().memory_info().rss > self.settings.max_rss_mb * 1024**2:
            raise ServiceError('memory_limit')
        async with self.limit:
            waited=0.0
            for attempt in range(3):
                emit('provider_request', 'started', host=urlsplit(url).hostname, method=method, attempt=attempt+1)
                try:
                    response = await self.client.request(method, url, **kwargs)
                except httpx.TimeoutException:
                    if attempt == 2: raise ServiceError('timeout') from None
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue
                except httpx.HTTPError:
                    raise ServiceError('connection_error') from None
                emit('provider_request', 'completed' if response.status_code<400 else 'failed', host=urlsplit(url).hostname, http_status=response.status_code, attempt=attempt+1)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == 2: raise ServiceError(f'http_{response.status_code}')
                    try: delay = float(response.headers.get('retry-after', '1'))
                    except ValueError: delay = 1
                    if not math.isfinite(delay):raise ServiceError('rate_limited')
                    ceiling=60 if response.status_code==429 else 5
                    if delay > ceiling or waited+max(0,delay)>60:raise ServiceError('rate_limited')
                    delay=max(0,delay)
                    emit('provider_retry_wait','started',host=urlsplit(url).hostname,http_status=response.status_code,retry_after_seconds=delay)
                    waited+=delay
                    await asyncio.sleep(delay)
                    emit('provider_retry_wait','completed',host=urlsplit(url).hostname,http_status=response.status_code,retry_after_seconds=delay)
                    continue
                if response.is_error: raise ServiceError(f'http_{response.status_code}')
                try: payload = response.json()
                except ValueError: raise ServiceError('invalid_json') from None
                if not isinstance(payload, dict): raise ServiceError('invalid_response')
                if payload.get('success') is False: raise ServiceError('provider_rejected')
                return payload
        raise ServiceError('retry_exhausted')
