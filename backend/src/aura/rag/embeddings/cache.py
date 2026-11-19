"""
FILE: backend/src/aura/rag/embeddings/cache.py
PURPOSE: Cache hosted embedding vectors by model and text hash.
MAIN RESPONSIBILITY: Embeddings And Cache.
INPUTS: Text batches and the shared model gateway.
OUTPUTS: Validated 1024-dimensional vectors in input order.
IMPORTANT FUNCTIONS / CLASSES: Embeddings.
CONNECTED MODULES: aura.observability.events, aura.core, aura.rag.ingestion.documents.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py.
PRESENTATION EXPLANATION: "Repeated text can reuse SQLite-cached vectors instead of another embedding request."
"""
# PRESENTATION SECTION: EMBEDDINGS AND CACHE
from aura.observability.events import traced, emit, span
import asyncio, json, math, sqlite3
from pathlib import Path
from aura.core import ServiceError
from aura.rag.ingestion.documents import digest

class Embeddings:
    """Model-specific SQLite embedding cache. Takes a Gateway and database path; embed returns validated vectors and avoids repeated remote requests for cached text."""
    model='@cf/baai/bge-m3'
    dimension=1024
    def __init__(self,gateway,path: Path):
        self.gateway=gateway
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, vector TEXT)')
        self.lock=asyncio.Lock(); self.calls=0; self.characters=0
    @traced('embeddings')
    async def embed(self,texts: list[str]) -> list[list[float]]:
        """Purpose: Embedding cache.
        
        Inputs: List of non-empty texts, each at most 2000 characters.
        Process and rationale: Look up model/text-hash keys, call Gateway.embed for missing vectors in batches of at most 16, validate and persist vectors.
        Returns: 1024-dimensional vectors in the same order as the input.
        """
        if any(not t.strip() or len(t)>2000 for t in texts): raise ServiceError('embedding_input_limit')
        async with self.lock:
            output=[]
            for start in range(0,len(texts),16):
                batch=texts[start:start+16]; vectors=[]; missing=[]
                for i,t in enumerate(batch):
                    row=self.db.execute('SELECT vector FROM cache WHERE key=?',(self.model+digest(t.encode()),)).fetchone()
                    vectors.append(json.loads(row[0]) if row else None)
                    if not row: missing.append(i)
                emit("embedding_cache", hits=len(batch)-len(missing), misses=len(missing), model=self.model, dimensions=self.dimension)
                if missing:
                    with span('embedding_request',texts=len(missing),model=self.model):
                        fetched=await self.gateway.embed([batch[i] for i in missing])
                    self.calls+=1
                    self.characters+=sum(len(batch[i]) for i in missing)
                    if len(fetched)!=len(missing): raise ServiceError('invalid_vectors')
                    for i,v in zip(missing,fetched):
                        self.validate(v); vectors[i]=v
                        self.db.execute('INSERT OR REPLACE INTO cache VALUES (?,?)',(self.model+digest(batch[i].encode()),json.dumps(v)))
                    self.db.commit()
                with span('embedding_validation',vectors=len(vectors),dimensions=self.dimension):
                    for v in vectors: self.validate(v)
                output.extend(vectors)
            return output
    def validate(self,v):
        if len(v)!=self.dimension or any(not math.isfinite(x) for x in v): raise ServiceError('embedding_dimension_mismatch')
    def close(self): self.db.close()
