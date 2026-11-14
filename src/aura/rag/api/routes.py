"""Validated document and RAG HTTP routes."""
from fastapi import APIRouter, Request, UploadFile, HTTPException
from pydantic import BaseModel, Field
from aura.core import ServiceError
router=APIRouter()
class Search(BaseModel):
    question: str=Field(min_length=1,max_length=2000)
    document_id: str | None=None
    top_k: int=Field(default=4,ge=1,le=5)
def service(r): return r.app.state.rag
@router.post('/documents/upload')
async def upload(request: Request,file: UploadFile,strategy: str='recursive'):
    if strategy not in ('recursive','semantic'): raise HTTPException(422,'invalid_strategy')
    data=await file.read(5*1024*1024+1)
    try: return await service(request).ingest(file.filename or '',data,strategy)
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
    return {'collection':p.store.collection,'embedding_model':p.embedding.model,'embedding_dimensions':1024,'embedding_calls':p.embedding.calls,'input_characters':p.embedding.characters,'quota_remaining':'unknown','ocr':'unavailable','documents':len(p.documents())}
