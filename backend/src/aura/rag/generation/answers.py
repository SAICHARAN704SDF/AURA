"""
FILE: backend/src/aura/rag/generation/answers.py
PURPOSE: Define answer records and validate quote-to-chunk references.
MAIN RESPONSIBILITY: Answer Citations.
INPUTS: Generated Answer and retrieved chunks.
OUTPUTS: Validated citations or ServiceError.
IMPORTANT FUNCTIONS / CLASSES: Citation, Answer, validate_citations.
CONNECTED MODULES: aura.core, aura.rag.ingestion.documents.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py.
PRESENTATION EXPLANATION: "A quotation must exist in its referenced chunk; this check alone does not prove entailment."
"""
# PRESENTATION SECTION: ANSWER CITATIONS
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
    """Purpose: Citation validation.
    
    Inputs: Answer and retrieved chunks.
    Process and rationale: Check required references and literal quote membership in trusted chunks; this is provenance validation rather than semantic entailment.
    Returns: No value on success, ServiceError on invalid or missing citations.
    """
    by_id={c.id:c for c in context}
    for c in answer.citations:
        if c.chunk_id not in by_id or c.quote not in by_id[c.chunk_id].text: raise ServiceError('invalid_citation')
    if not answer.insufficient_evidence and not answer.citations: raise ServiceError('missing_citations')
