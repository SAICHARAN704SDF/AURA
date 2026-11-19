"""A committed upload survives worker loss; only one queue consumer runs per directory."""
import asyncio
from contextlib import suppress
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from aura.core import ServiceError
from aura.observability.events import EventBus
from aura.rag.api.ingestion_jobs import router
from aura.rag.ingestion.jobs import IngestionQueue, MAX_ATTEMPTS


class Documents:
    def __init__(self):
        self.seen = set()
        self.failure = None

    async def ingest(self, name, data, strategy, **kwargs):
        if self.failure:
            raise ServiceError(self.failure)
        duplicate = data in self.seen
        self.seen.add(data)
        return {"document":SimpleNamespace(id="document-1"),"duplicate":duplicate,"chunks":1}


async def wait_status(queue, identifier, status):
    async with asyncio.timeout(5):
        while queue.get(identifier)["status"] != status:
            await asyncio.sleep(0.015)
    return queue.get(identifier)


def test_recovery_after_index_commit(tmp_path):
    async def run():
        documents = Documents()
        indexed = asyncio.Event()
        class Interrupted:
            async def ingest(self,*args,**kwargs):
                await documents.ingest(*args,**kwargs)
                indexed.set()
                await asyncio.Event().wait()
        first = IngestionQueue(tmp_path,Interrupted())
        first.start()
        job = first.enqueue(payload=b"durable",name="report.txt",strategy="recursive",threshold=.8)
        await asyncio.wait_for(indexed.wait(),5)
        backup = IngestionQueue(tmp_path,documents)
        backup.start()
        await asyncio.sleep(.05)
        assert backup.get(job["id"])["attempts"] == 1
        first.worker.cancel()
        with suppress(asyncio.CancelledError):
            await first.close()
        done = await wait_status(backup,job["id"],"completed")
        assert done["duplicate"] and done["attempts"]==2
        assert backup.db.execute("SELECT payload FROM ingestion_jobs").fetchone()[0] is None
        await backup.close()
    asyncio.run(run())


def test_retry_and_permanent_validation(tmp_path):
    async def run():
        documents = Documents()
        q = IngestionQueue(tmp_path,documents)
        job = q.enqueue(payload=b"retry me",name="report.txt",strategy="fixed",threshold=.8)
        documents.failure = "http_429"
        for attempt in range(MAX_ATTEMPTS):
            await q._execute(q._claim())
            assert q.get(job["id"])["attempts"] == attempt+1
            if attempt<MAX_ATTEMPTS-1:
                assert q.get(job["id"])["available_after"] > q.get(job["id"])["updated"]
                with q.db:
                    q.db.execute("UPDATE ingestion_jobs SET available_after=0 WHERE id=?",(job["id"],))
        assert q.get(job["id"])["retryable"]
        q.retry(job["id"])
        documents.failure = None
        await q._execute(q._claim())
        assert q.get(job["id"])["status"]=="completed"
        invalid = q.enqueue(payload=b"invalid",name="x.bin",strategy="recursive",threshold=.8)
        documents.failure = "unsupported_file_type"
        await q._execute(q._claim())
        assert not q.get(invalid["id"])["retryable"]
        with pytest.raises(ServiceError,match="ingestion_job_not_retryable"):
            q.retry(invalid["id"])
        assert q.discard_failed(invalid["id"])["status"]=="discarded"
        await q.close()
    asyncio.run(run())


def test_upload_and_url_http_poll(tmp_path,monkeypatch):
    from contextlib import asynccontextmanager
    import time
    calls=[]
    def fetch(source):
        calls.append(source)
        return "article.md",b"body","https://example.org/articles/paper"
    monkeypatch.setattr("aura.rag.ingestion.jobs.fetch",fetch)
    @asynccontextmanager
    async def lifespan(app):
        app.state.ingestion = IngestionQueue(tmp_path,Documents(),EventBus())
        app.state.ingestion.start()
        yield
        await app.state.ingestion.close()
    app=FastAPI(lifespan=lifespan)
    app.include_router(router)
    with TestClient(app) as client:
        upload=client.post("/ingestion/jobs/upload",files={"file":("report.txt",b"snow", "text/plain")})
        imported=client.post("/ingestion/jobs/import",json={"source":"https://example.org/articles/paper"})
        for response in [upload,imported]:
            assert response.status_code==202
            identifier=response.json()["id"]
            for _ in range(100):
                status=client.get("/ingestion/jobs/"+identifier).json()
                if status["status"]=="completed":
                    break
                time.sleep(.01)
            assert status["document_id"]=="document-1" and status["chunks"]==1
        assert calls==["https://example.org/articles/paper"]
