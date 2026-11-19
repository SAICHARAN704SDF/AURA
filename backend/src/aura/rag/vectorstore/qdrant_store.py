"""
FILE: backend/src/aura/rag/vectorstore/qdrant_store.py
PURPOSE: Persist and query chunk vectors in a checked Qdrant collection.
MAIN RESPONSIBILITY: Vector Storage.
INPUTS: Chunks, vectors and optional document filter.
OUTPUTS: Stored or retrieved Chunk records.
IMPORTANT FUNCTIONS / CLASSES: Store.
CONNECTED MODULES: aura.core, aura.rag.ingestion.documents.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py.
PRESENTATION EXPLANATION: "Qdrant stores vectors and chunk payloads; SQLite holds separate metadata and workflow state."
"""
# PRESENTATION SECTION: VECTOR STORAGE
from pathlib import Path
from qdrant_client import QdrantClient, models
from aura.core import ServiceError
from aura.rag.ingestion.documents import Chunk

class Store:
    """Qdrant collection adapter for source-labelled chunks. Takes a local path or remote URL and validates the existing collection dimension and distance before use."""
    collection='aura_bge_m3_1024_v1'
    def __init__(self,path: Path, url: str | None=None, *, collection=None, dimension=1024):
        self.collection=collection or self.collection
        self.client=QdrantClient(url=url) if url else QdrantClient(path=str(path))
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection,vectors_config=models.VectorParams(size=dimension,distance=models.Distance.COSINE))
        config=self.client.get_collection(self.collection).config.params.vectors
        if config.size!=dimension or config.distance!=models.Distance.COSINE: raise ServiceError('collection_dimension_mismatch')
    def upsert(self,chunks,vectors):
        """Purpose: Vector storage.
        
        Inputs: Chunk records and corresponding vectors.
        Process and rationale: Write each chunk ID, vector and source payload into the configured Qdrant collection.
        Returns: Qdrant storage side effect; no application return value.
        """
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
        """Purpose: Vector search.
        
        Inputs: Query vector, result count and optional document ID.
        Process and rationale: Call Qdrant query_points with a document filter so semantic candidates retain their source scope.
        Returns: Chunk records recovered from stored payloads.
        """
        return [Chunk.model_validate(p.payload) for p in self.client.query_points(self.collection,query=vector,limit=k,query_filter=self.filter(document_id)).points]
    def delete(self,id): self.client.delete(self.collection,points_selector=models.FilterSelector(filter=self.filter(id)))
    def close(self): self.client.close()
