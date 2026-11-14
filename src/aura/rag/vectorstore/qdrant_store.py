"""Persistent Qdrant vector storage."""
from pathlib import Path
from qdrant_client import QdrantClient, models
from aura.core import ServiceError
from aura.rag.ingestion.documents import Chunk

class Store:
    collection='aura_bge_m3_1024_v1'
    def __init__(self,path: Path, url: str | None=None):
        self.client=QdrantClient(url=url) if url else QdrantClient(path=str(path))
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection,vectors_config=models.VectorParams(size=1024,distance=models.Distance.COSINE))
        config=self.client.get_collection(self.collection).config.params.vectors
        if config.size!=1024 or config.distance!=models.Distance.COSINE: raise ServiceError('collection_dimension_mismatch')
    def upsert(self,chunks,vectors):
        self.client.upsert(self.collection,points=[models.PointStruct(id=c.id,vector=v,payload=c.model_dump()) for c,v in zip(chunks,vectors)])
    def all(self,document_id=None):
        filt=self.filter(document_id); result=[]; offset=None
        while True:
            points,offset=self.client.scroll(self.collection,scroll_filter=filt,limit=128,offset=offset,with_vectors=False)
            result.extend(Chunk.model_validate(p.payload) for p in points)
            if offset is None: return result
    def filter(self,id):
        return models.Filter(must=[models.FieldCondition(key='document_id',match=models.MatchValue(value=id))]) if id else None
    def search(self,vector,k,document_id=None):
        return [Chunk.model_validate(p.payload) for p in self.client.query_points(self.collection,query=vector,limit=k,query_filter=self.filter(document_id)).points]
    def delete(self,id): self.client.delete(self.collection,points_selector=models.FilterSelector(filter=self.filter(id)))
    def close(self): self.client.close()
