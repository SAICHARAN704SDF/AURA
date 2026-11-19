"""
FILE: backend/src/aura/rag/pipeline.py
PURPOSE: Coordinate persistent ingestion and delegate retrieval and generation.
MAIN RESPONSIBILITY: Rag Pipeline.
INPUTS: Gateway, storage path, file bytes, question and optional document scope.
OUTPUTS: Document metadata, retrieval results or cited answer.
IMPORTANT FUNCTIONS / CLASSES: Pipeline.
CONNECTED MODULES: aura.observability.events, aura.core, aura.rag.ingestion.documents, aura.rag.chunking.chunker, aura.rag.embeddings.cache, aura.rag.vectorstore.qdrant_store, aura.rag.retrieval.ranking, aura.rag.generation.answers, aura.rag.generation.generator, aura.rag.retrieval.retriever, aura.rag.ingestion.documents.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py.
PRESENTATION EXPLANATION: "This is the central RAG service: upload prepares the index; asking reuses it."
"""
# PRESENTATION SECTION: RAG PIPELINE
from aura.observability.events import traced, emit, span
import asyncio
from pathlib import Path
from aura.core import ServiceError
from aura.rag.ingestion.documents import Document, Chunk, load
from aura.rag.chunking.chunker import chunks, semantic_chunks
from aura.rag.embeddings.cache import Embeddings
from aura.rag.vectorstore.qdrant_store import Store
from aura.rag.retrieval.ranking import cosine
from aura.rag.generation.answers import Answer, Citation, validate_citations
from aura.rag.generation.generator import query as generate_answer
from aura.rag.retrieval.retriever import search as retrieve

class Pipeline:
    """Shared document service owning Qdrant, SQLite metadata/cache and ingestion locking. Constructed by create_app; API routes delegate ingestion, search and answers here."""
    def __init__(self,gateway,path: Path,url=None, *, local_embedding=False):
        path.mkdir(parents=True,exist_ok=True)
        self.gateway=gateway; self.path=path
        from aura.rag.embeddings.local import LocalMiniLM
        self.local_embedding = local_embedding
        encoder=LocalMiniLM() if local_embedding else gateway
        self.store=Store(path/'vectors',url,collection='aura_minilm_384_v1' if local_embedding else None,
                         dimension=384 if local_embedding else 1024)
        self.embedding=Embeddings(encoder,path/'embeddings.sqlite')
        if local_embedding:
            self.embedding.model, self.embedding.dimension = encoder.model, encoder.dimension
        self.lock=asyncio.Lock()
        self.db=self.embedding.db
        self.db.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, body TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS mutations (id TEXT PRIMARY KEY)'); self.db.commit()
        for (id,) in self.db.execute('SELECT id FROM mutations').fetchall():
            self.store.delete(id)
            with self.db:
                self.db.execute('DELETE FROM documents WHERE id=?',(id,))
                self.db.execute('DELETE FROM mutations WHERE id=?',(id,))
        from aura.memory.profiles import Profiles
        self.profiles = Profiles(self.db)
        self.corpus_cache={}
    def documents(self): return [Document.model_validate_json(r[0]) for r in self.db.execute('SELECT body FROM documents')]
    def document(self,id):
        row=self.db.execute('SELECT body FROM documents WHERE id=?',(id,)).fetchone()
        if not row: raise ServiceError('document_not_found')
        return Document.model_validate_json(row[0])
    @traced('ingestion')
    async def ingest(self,name,data,strategy='recursive', *, threshold=0.8, source_url=None):
        """Purpose: RAG ingestion.
        
        Inputs: Filename, bytes and chunking strategy.
        Process and rationale: Serialize ingestion, call load and chunks, optionally merge similar adjacent blocks, embed, journal vector writes and persist document metadata.
        Returns: Document metadata, duplicate flag and, for new uploads, chunk count and actual strategy.
        """
        async with self.lock:
            # STEP 1: Extract source pages before checking content-derived duplicate identity.
            doc=await asyncio.to_thread(load,name,data)
            existing = self.db.execute('SELECT body FROM documents WHERE id=?',(doc.id,)).fetchone()
            if existing:
                saved = Document.model_validate_json(existing[0])
                if source_url and not saved.source_url:
                    saved.source_url = source_url
                    with self.db:
                        self.db.execute('UPDATE documents SET body=? WHERE id=?',(saved.model_dump_json(),saved.id))
                return {'document':saved,'duplicate':True}
            doc.source_url = source_url
            emit('ocr_decision','info', applied_pages=sum(page.ocr_applied for page in doc.pages), required_pages=sum(page.requires_ocr for page in doc.pages))
            # STEP 2: Preserve source offsets while preparing searchable passages.
            actual='recursive' if strategy == 'semantic' else strategy
            cs=chunks(doc, strategy=actual)
            emit('chunk_inventory', chunks=len(cs), pages=len(doc.pages), strategy=strategy)
            if len(cs)>1000: raise ServiceError('chunk_limit')
            if strategy=='semantic' and cs:
                try:
                    cs=await semantic_chunks(doc,self.embedding.embed,threshold); actual='semantic'
                    emit('semantic_chunking', 'completed', chunks=len(cs))
                except ServiceError as e:
                    if e.code not in ('http_429','rate_limited'): raise
                    actual='recursive_after_semantic_quota'
            if len(cs)>1000: raise ServiceError('chunk_limit')
            # STEP 3: Resolve vectors through the cache, then journal cross-store writes.
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
    async def search(self,question,k=4,document_id=None,*,project_id=None):
        if not 1 <= k <= 5:
            raise ServiceError('invalid_search')
        adaptive = project_id and self.profiles.get(project_id).adaptive_retrieval
        result = await retrieve(self,question,min(5,k+1) if adaptive else k,document_id)
        if adaptive:
            result['chunks'] = self.profiles.rank(project_id,result['chunks'])[:k]
            result['personalized'] = True
        return result
    async def query(self,question,document_id=None):
        return await generate_answer(self,question,document_id)
    def close(self): self.store.close(); self.embedding.close()
