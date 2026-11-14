"""Cached cloud embeddings."""
from aura.observability.events import traced, emit, span
import asyncio, json, math, sqlite3
from pathlib import Path
from aura.core import ServiceError
from aura.rag.ingestion.documents import digest

class Embeddings:
    model='@cf/baai/bge-m3'
    dimension=1024
    def __init__(self,gateway,path: Path):
        self.gateway=gateway
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, vector TEXT)')
        self.lock=asyncio.Lock(); self.calls=0; self.characters=0
    @traced('embeddings')
    async def embed(self,texts: list[str]) -> list[list[float]]:
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
                    fetched=await self.gateway.embed([batch[i] for i in missing]); self.calls+=1
                    self.characters+=sum(len(batch[i]) for i in missing)
                    if len(fetched)!=len(missing): raise ServiceError('invalid_vectors')
                    for i,v in zip(missing,fetched):
                        self.validate(v); vectors[i]=v
                        self.db.execute('INSERT OR REPLACE INTO cache VALUES (?,?)',(self.model+digest(batch[i].encode()),json.dumps(v)))
                    self.db.commit()
                for v in vectors: self.validate(v)
                output.extend(vectors)
            return output
    def validate(self,v):
        if len(v)!=self.dimension or any(not math.isfinite(x) for x in v): raise ServiceError('embedding_dimension_mismatch')
    def close(self): self.db.close()
