"""
FILE: backend/src/aura/rag/api/routes.py
PURPOSE: Validate HTTP input and delegate to the shared RAG pipeline.
MAIN RESPONSIBILITY: Document And Rag Api.
INPUTS: UploadFile, query body and FastAPI request.
OUTPUTS: Document, search, answer or status response.
IMPORTANT FUNCTIONS / CLASSES: Search, service, upload, listing, get, delete, search, query, status.
CONNECTED MODULES: aura.core.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py.
PRESENTATION EXPLANATION: "Routes handle HTTP concerns while the pipeline implements document processing."
"""
# PRESENTATION SECTION: DOCUMENT AND RAG API
from typing import Literal
from fastapi import Query, APIRouter, Request, UploadFile, HTTPException
from pydantic import BaseModel, Field
from aura.core import ServiceError
router=APIRouter()
class Search(BaseModel):
    question: str=Field(min_length=1,max_length=2000)
    document_id: str | None=None
    top_k: int=Field(default=4,ge=1,le=5)
def service(r): return r.app.state.rag
@router.post('/documents/upload')
async def upload(request: Request,file: UploadFile,strategy: str='recursive',threshold: float=Query(0.8,ge=-1,le=1)):
    """Purpose: Document upload API.
    
    Inputs: Request, UploadFile and recursive/semantic strategy.
    Process and rationale: Read at most the upload limit plus one byte, call Pipeline.ingest and close the uploaded file even on failure.
    Returns: Ingestion response containing document and duplicate status.
    """
    if strategy not in ('recursive','semantic','fixed','sentence','structure'): raise HTTPException(422,'invalid_strategy')
    data=await file.read(5*1024*1024+1)
    try: return await service(request).ingest(file.filename or '',data,strategy,threshold=threshold)
    finally: await file.close()
@router.get('/documents')
async def listing(request: Request): return service(request).documents()
@router.get('/documents/{id}')
async def get(id: str,request: Request): return service(request).document(id)
@router.delete('/documents/{id}')
async def delete(id: str,request: Request):
    await service(request).delete(id); return {'deleted':True}
@router.post('/retrieval/search')
async def search(body: Search,request: Request): return await service(request).search(body.question,body.top_k,body.document_id)
@router.post('/rag/query')
async def query(body: Search,request: Request): return await service(request).query(body.question,body.document_id)
@router.get('/rag/status')
async def status(request: Request):
    p=service(request)
    return {'collection':p.store.collection,'embedding_model':p.embedding.model,'embedding_dimensions':p.embedding.dimension,'embedding_calls':p.embedding.calls,'input_characters':p.embedding.characters,'quota_remaining':'unknown','ocr':__import__('aura.rag.ingestion.ocr',fromlist=['status']).status(),'documents':len(p.documents())}

class SourceImport(BaseModel):
    source: str = Field(min_length=1, max_length=2000)
    strategy: Literal['recursive','fixed','structure','semantic','sentence'] = 'recursive'
    threshold: float = Field(default=0.8,ge=-1,le=1)

@router.post('/documents/import')
async def import_source(body: SourceImport, request: Request):
    import asyncio
    from aura.rag.ingestion.public_web import fetch
    name, data, url = await asyncio.to_thread(fetch, body.source.strip())
    return await service(request).ingest(name,data,body.strategy,threshold=body.threshold,source_url=url)
