"""Small synthetic lexical relevance/citation benchmark; not an LLM quality claim."""
import json
from pathlib import Path
import pytest
from aura.rag.ingestion.documents import load
from aura.rag.chunking.chunker import chunks
from aura.rag.retrieval.ranking import sparse
from aura.rag.generation.answers import Answer,Citation,validate_citations
from aura.core import ServiceError

DATA=json.loads((Path(__file__).parent/'fixtures/retrieval_cases.json').read_text())
@pytest.mark.parametrize('case',DATA['queries'])
def test_expected_retrieval_and_quote(case):
    corpus=[c for d in DATA['documents'] for c in chunks(load(d['name'],d['text'].encode()))]
    results=sparse(case['question'],corpus)
    if case['expected'] is None:
        assert results==[];return
    assert results[0].filename==case['expected']
    answer=Answer(answer=case['quote'],insufficient_evidence=False,citations=[Citation(chunk_id=results[0].id,quote=case['quote'])])
    validate_citations(answer,results)
    answer.citations[0].quote='fabricated quotation'
    with pytest.raises(ServiceError,match='invalid_citation'):validate_citations(answer,results)
