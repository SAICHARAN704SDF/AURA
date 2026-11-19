"""Offline evidence fidelity; this is not an LLM quality benchmark."""
from aura.rag.ingestion.documents import load
from aura.rag.chunking.chunker import chunks
from aura.rag.generation.context import evidence_payload
from aura.rag.generation.answers import Answer, Citation, validate_citations


def test_context_retains_exact_text_and_ids():
    evidence = chunks(load('research.txt', b'Exact evidence with\nline breaks.\nA reported result is 42.'))
    payload = evidence_payload(evidence)
    assert payload == [{'chunk_id':c.id,'text':c.text} for c in evidence]
    answer = Answer(answer='42', insufficient_evidence=False,
                    citations=[Citation(chunk_id=evidence[0].id, quote='42')])
    validate_citations(answer, evidence)
