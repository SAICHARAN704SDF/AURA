"""A durable single-worker ingestion queue for local SQLite deployments.

A POSIX file lock elects one worker for the data directory. A lost worker releases
the lock in the kernel. Its successor can then safely recover unacknowledged jobs.
Uploads and queue state commit together. The existing content-based ingest path
makes replay after an index commit safe.
"""
import asyncio
import fcntl
import sqlite3
import time
import uuid
from pathlib import Path

from aura.core import ServiceError
from aura.observability.events import current_bus, current_trace, emit
from .public_web import fetch

RETRYABLE = {"timeout", "connection_error", "rate_limited", "http_429", "http_502", "http_503",
             "http_504", "source_timeout", "source_unavailable", "source_policy_unavailable",
             "worker_interrupted"}
MAX_ATTEMPTS = 3
MAX_UPLOAD = 5 * 1024 * 1024
PROJECTION = """id, kind, name, status, attempts, error, document_id, duplicate, chunks,
                created, updated, trace_id, available_after"""


class IngestionQueue:
    def __init__(self, directory: Path, pipeline, telemetry=None):
        self.directory = directory
        self.pipeline = pipeline
        self.telemetry = telemetry
        self.db = sqlite3.connect(directory / "ingestion-jobs.sqlite", timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS ingestion_jobs (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT, source TEXT, payload BLOB,
            strategy TEXT NOT NULL, threshold REAL NOT NULL, trace_id TEXT NOT NULL,
            status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
            document_id TEXT, duplicate INTEGER, chunks INTEGER, created REAL NOT NULL,
            updated REAL NOT NULL, available_after REAL NOT NULL DEFAULT 0)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS ingestion_ready ON ingestion_jobs(status,available_after,created)")
        self.db.commit()
        self.wake = asyncio.Event()
        self.stopping = False
        self.worker = None

    def enqueue(self, *, strategy, threshold, name=None, payload=None, source=None, trace_id=""):
        upload = payload is not None
        if upload and (not payload or len(payload) > MAX_UPLOAD):
            raise ServiceError("invalid_file_size")
        if not upload and not source:
            raise ServiceError("invalid_public_url")
        now, identifier = time.time(), uuid.uuid4().hex
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            count, used = self.db.execute("""SELECT count(*), coalesce(sum(length(payload)),0)
                FROM ingestion_jobs WHERE status IN ('queued','running') OR
                (status='failed' AND (source IS NOT NULL OR payload IS NOT NULL))""").fetchone()
            if count >= 32 or used + len(payload or b"") > 64 * 1024 * 1024:
                raise ServiceError("ingestion_queue_full")
            self.db.execute("""INSERT INTO ingestion_jobs
                (id,kind,name,payload,source,strategy,threshold,trace_id,status,created,updated)
                VALUES (?,?,?,?,?,?,?,?,'queued',?,?)""",
                (identifier, "upload" if upload else "url", name, payload, source, strategy, threshold,
                 trace_id or identifier, now, now))
        self.wake.set()
        return self.get(identifier)

    def get(self, identifier):
        row = self.db.execute(f"SELECT {PROJECTION} FROM ingestion_jobs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ServiceError("ingestion_job_not_found")
        result = dict(row)
        result["duplicate"] = None if row["duplicate"] is None else bool(row["duplicate"])
        result["retryable"] = row["status"] == "failed" and row["error"] in RETRYABLE
        return result

    def retry(self, identifier):
        job = self.get(identifier)
        if not job["retryable"]:
            raise ServiceError("ingestion_job_not_retryable")
        with self.db:
            changed = self.db.execute("""UPDATE ingestion_jobs SET status='queued',error=NULL,
                available_after=0,updated=? WHERE id=? AND status='failed' AND
                (payload IS NOT NULL OR source IS NOT NULL)""", (time.time(),identifier)).rowcount
            if not changed:
                raise ServiceError("ingestion_job_not_retryable")
        self.wake.set()
        return self.get(identifier)

    def discard_failed(self, identifier):
        self.get(identifier)
        with self.db:
            updated = self.db.execute("""UPDATE ingestion_jobs SET status='discarded', payload=NULL,
                source=NULL,updated=? WHERE id=? AND status='failed'""",(time.time(),identifier)).rowcount
        if not updated:
            raise ServiceError("ingestion_job_not_failed")
        return self.get(identifier)

    def start(self):
        self.worker = asyncio.create_task(self._run(), name="researchos-ingestion")

    async def close(self):
        self.stopping = True
        self.wake.set()
        try:
            if self.worker:
                await self.worker
        finally:
            self.db.close()

    async def _wait(self):
        try:
            await asyncio.wait_for(self.wake.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            pass
        self.wake.clear()

    def _recover(self):
        now = time.time()
        with self.db:
            self.db.execute("""UPDATE ingestion_jobs SET
                status=CASE WHEN attempts>=? THEN 'failed' ELSE 'queued' END,
                error='worker_interrupted', available_after=0, updated=? WHERE status='running'""",
                (MAX_ATTEMPTS, now))

    def _claim(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("""SELECT * FROM ingestion_jobs WHERE status='queued'
                AND available_after<=? ORDER BY created,id LIMIT 1""", (time.time(),)).fetchone()
            if row:
                self.db.execute("""UPDATE ingestion_jobs SET status='running',attempts=attempts+1,
                    error=NULL,updated=? WHERE id=?""", (time.time(),row["id"]))
        return row

    async def _execute(self, row):
        trace = current_trace.set(row["trace_id"])
        bus = current_bus.set(self.telemetry)
        try:
            emit("ingestion_job","started", job_id=row["id"], attempt=row["attempts"]+1)
            name, data, url = row["name"], row["payload"], None
            if row["kind"] == "url":
                name, data, url = await asyncio.to_thread(fetch, row["source"])
            result = await self.pipeline.ingest(name,data,row["strategy"],threshold=row["threshold"],source_url=url)
            with self.db:
                self.db.execute("""UPDATE ingestion_jobs SET status='completed', document_id=?, name=?,
                    duplicate=?, chunks=?, payload=NULL, source=NULL, updated=? WHERE id=?""",
                    (result["document"].id,name,bool(result["duplicate"]),result.get("chunks"),time.time(),row["id"]))
            emit("ingestion_job","completed",job_id=row["id"])
        except Exception as exc:
            error = exc.code if isinstance(exc,ServiceError) else "ingestion_internal_error"
            retryable = error in RETRYABLE
            attempt = row["attempts"] + 1
            pending = retryable and attempt < MAX_ATTEMPTS
            now = time.time()
            with self.db:
                self.db.execute("""UPDATE ingestion_jobs SET status=?,error=?,updated=?,available_after=?,
                    payload=CASE WHEN ? THEN payload ELSE NULL END, source=CASE WHEN ? THEN source ELSE NULL END
                    WHERE id=?""", ("queued" if pending else "failed",error,now,
                    now + 2**attempt if pending else 0,retryable,retryable,row["id"]))
            emit("ingestion_job","retrying" if pending else "failed",job_id=row["id"],error=error)
        finally:
            current_trace.reset(trace)
            current_bus.reset(bus)

    async def _run(self):
        with (self.directory / "ingestion-worker.lock").open("a+b") as lock:
            while not self.stopping:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    await self._wait()
            else:
                return
            self._recover()
            while not self.stopping:
                row = self._claim()
                if row:
                    await self._execute(row)
                else:
                    await self._wait()
