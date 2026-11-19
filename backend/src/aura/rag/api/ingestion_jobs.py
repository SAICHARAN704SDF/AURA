"""Submit durable document work, observe state, or explicitly release a failed upload."""
from typing import Literal
from pathlib import PurePath

from fastapi import APIRouter, Query, Request, UploadFile

from aura.observability.events import current_trace
from aura.rag.ingestion.jobs import MAX_UPLOAD
from .routes import SourceImport

router = APIRouter(prefix="/ingestion/jobs")


@router.post("/upload", status_code=202)
async def enqueue_upload(request: Request, file: UploadFile,
                         strategy: Literal["recursive","fixed","sentence","structure","semantic"]="recursive",
                         threshold: float=Query(0.8,ge=-1,le=1)):
    try:
        data = await file.read(MAX_UPLOAD+1)
        name = PurePath((file.filename or "upload").replace("\\","/")).name[:240]
        return request.app.state.ingestion.enqueue(name=name,payload=data,strategy=strategy,
                                                   threshold=threshold,trace_id=current_trace.get())
    finally:
        await file.close()


@router.post("/import", status_code=202)
async def enqueue_import(body: SourceImport, request: Request):
    return request.app.state.ingestion.enqueue(source=body.source.strip(),strategy=body.strategy,
                                              threshold=body.threshold,trace_id=current_trace.get())


@router.get("/{identifier}")
async def job(identifier: str, request: Request):
    return request.app.state.ingestion.get(identifier)


@router.post("/{identifier}/retry", status_code=202)
async def retry(identifier: str, request: Request):
    return request.app.state.ingestion.retry(identifier)


@router.delete("/{identifier}")
async def discard_failed(identifier: str, request: Request):
    return request.app.state.ingestion.discard_failed(identifier)
