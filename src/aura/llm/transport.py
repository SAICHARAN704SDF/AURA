"""Bounded asynchronous HTTP, retries and process resource guard."""
import asyncio
from urllib.parse import urlsplit
from aura.observability.events import emit
import httpx
import psutil
from aura.core import Settings, ServiceError

class Transport:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=settings.timeout, follow_redirects=False)
        self.owned = client is None
        self.limit = asyncio.Semaphore(settings.concurrency)

    async def close(self) -> None:
        if self.owned:
            await self.client.aclose()

    async def request(self, method: str, url: str, **kwargs) -> dict:
        if psutil.Process().memory_info().rss > self.settings.max_rss_mb * 1024**2:
            raise ServiceError('memory_limit')
        async with self.limit:
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
                    if delay > 5: raise ServiceError('rate_limited')
                    await asyncio.sleep(max(0, delay))
                    continue
                if response.is_error: raise ServiceError(f'http_{response.status_code}')
                try: payload = response.json()
                except ValueError: raise ServiceError('invalid_json') from None
                if not isinstance(payload, dict): raise ServiceError('invalid_response')
                if payload.get('success') is False: raise ServiceError('provider_rejected')
                return payload
        raise ServiceError('retry_exhausted')
