"""Persistent ingestion, hybrid retrieval and cited generation."""
from aura.observability.events import traced, emit, span
import asyncio
from pathlib import Path
from aura.core import ServiceError
from aura.rag.ingestion.documents import Document, Chunk, load
from aura.rag.chunking.chunker import chunks
from aura.rag.embeddings.cache import Embeddings
from aura.rag.vectorstore.qdrant_store import Store
from aura.rag.retrieval.ranking import cosine
from aura.rag.generation.answers import Answer, Citation, validate_citations
from aura.rag.generation.generator import query as generate_answer
from aura.rag.retrieval.retriever import search as retrieve

class Pipeline:
    def __init__(self,gateway,path: Path,url=None):
        path.mkdir(parents=True,exist_ok=True)
        self.gateway=gateway; self.path=path
        self.store=Store(path/'vectors',url); self.embedding=Embeddings(gateway,path/'embeddings.sqlite')
        self.lock=asyncio.Lock()
        self.db=self.embedding.db
        self.db.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, body TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS mutations (id TEXT PRIMARY KEY)'); self.db.commit()
        for (id,) in self.db.execute('SELECT id FROM mutations').fetchall():
            self.store.delete(id)
            with self.db:
                self.db.execute('DELETE FROM documents WHERE id=?',(id,))
                self.db.execute('DELETE FROM mutations WHERE id=?',(id,))
        self.corpus_cache={}
    def documents(self): return [Document.model_validate_json(r[0]) for r in self.db.execute('SELECT body FROM documents')]
    def document(self,id):
        row=self.db.execute('SELECT body FROM documents WHERE id=?',(id,)).fetchone()
        if not row: raise ServiceError('document_not_found')
        return Document.model_validate_json(row[0])
    @traced('ingestion')
    async def ingest(self,name,data,strategy='recursive'):
        async with self.lock:
            doc=await asyncio.to_thread(load,name,data)
            if self.db.execute('SELECT 1 FROM documents WHERE id=?',(doc.id,)).fetchone(): return {'document':doc,'duplicate':True}
            cs=chunks(doc); actual='recursive'
            emit('chunk_inventory', chunks=len(cs), pages=len(doc.pages), strategy=strategy)
            if len(cs)>1000: raise ServiceError('chunk_limit')
            if strategy=='semantic' and cs:
                try:
                    # Adjacent paragraph-scale blocks merge when cosine similarity is high.
                    base=chunks(doc,600,0); vec=await self.embedding.embed([c.text for c in base]); merged=[]
                    for i,c in enumerate(base):
                        if merged and i and c.page==merged[-1].page and len(merged[-1].text)+len(c.text)<=1800 and cosine(vec[i-1],vec[i])>0.8:
                            prev=merged.pop(); text=prev.text+c.text
                            from aura.rag.ingestion.documents import digest
                            import uuid
                            merged.append(prev.model_copy(update={'text':text,'end':c.end,'content_hash':digest(text.encode()),'id':str(uuid.uuid5(uuid.NAMESPACE_URL,prev.id+c.id))}))
                        else: merged.append(c)
                    cs=merged; actual='semantic'
                    emit('semantic_chunking', 'completed', chunks=len(cs))
                except ServiceError as e:
                    if e.code not in ('http_429','rate_limited'): raise
                    actual='recursive_after_semantic_quota'
            vectors=await self.embedding.embed([c.text for c in cs]) if cs else []
            with self.db:self.db.execute('INSERT OR REPLACE INTO mutations VALUES (?)',(doc.id,))
            try:
                with span('vector_storage', chunks=len(cs)):
                    await asyncio.to_thread(self.store.upsert,cs,vectors) if cs else None
                self.db.execute('INSERT INTO documents VALUES (?,?)',(doc.id,doc.model_dump_json()))
                self.db.execute('DELETE FROM mutations WHERE id=?',(doc.id,)); self.db.commit(); self.corpus_cache.clear()
            except Exception:
                self.store.delete(doc.id); raise
            return {'document':doc,'duplicate':False,'chunks':len(cs),'strategy':actual}
    async def delete(self,id):
        async with self.lock:
            self.document(id)
            with self.db:self.db.execute('INSERT OR REPLACE INTO mutations VALUES (?)',(id,))
            await asyncio.to_thread(self.store.delete,id)
            self.db.execute('DELETE FROM documents WHERE id=?',(id,))
            self.db.execute('DELETE FROM mutations WHERE id=?',(id,)); self.db.commit();self.corpus_cache.clear()
    async def search(self,question,k=4,document_id=None):
        return await retrieve(self,question,k,document_id)
    async def query(self,question,document_id=None):
        return await generate_answer(self,question,document_id)
    def close(self): self.store.close(); self.embedding.close()
