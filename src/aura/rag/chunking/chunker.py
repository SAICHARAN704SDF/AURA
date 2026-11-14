"""Source-preserving document chunking."""
from aura.observability.events import traced, emit, span
import uuid
from aura.core import ServiceError
from aura.rag.ingestion.documents import Document, Chunk, digest

@traced('chunking')
def chunks(doc: Document, size: int=1200, overlap: int=150) -> list[Chunk]:
    if not 100<=size<=1800 or not 0<=overlap<size: raise ServiceError('invalid_chunk_config')
    result=[]
    for p in doc.pages:
        start=0
        while start<len(p.text):
            end=min(start+size,len(p.text))
            if end<len(p.text):
                boundary=p.text.rfind('\n',start+size//2,end)
                if boundary>start: end=boundary+1
            text=p.text[start:end]
            if text.strip():
                h=digest(text.encode())
                result.append(Chunk(id=str(uuid.uuid5(uuid.NAMESPACE_URL,f'{doc.id}:{p.number}:{start}:{end}')),document_id=doc.id,filename=doc.filename,page=p.number,start=start,end=end,text=text,content_hash=h))
            if end==len(p.text): break
            start=max(start+1,end-overlap)
    return result
