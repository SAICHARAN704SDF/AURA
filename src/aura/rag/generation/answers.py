"""Typed answers and citation identity validation (not entailment)."""
from pydantic import BaseModel, Field
from aura.core import ServiceError
from aura.rag.ingestion.documents import Chunk

class Citation(BaseModel):
    chunk_id: str
    quote: str = Field(min_length=1)
class Answer(BaseModel):
    answer: str
    insufficient_evidence: bool
    citations: list[Citation]

def validate_citations(answer: Answer, context: list[Chunk]) -> None:
    by_id={c.id:c for c in context}
    for c in answer.citations:
        if c.chunk_id not in by_id or c.quote not in by_id[c.chunk_id].text: raise ServiceError('invalid_citation')
    if not answer.insufficient_evidence and not answer.citations: raise ServiceError('missing_citations')
