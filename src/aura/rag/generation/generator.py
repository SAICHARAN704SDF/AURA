"""Answer generation over retrieved evidence, using the configured gateway."""
from aura.observability.events import traced, emit, span
import json
from aura.contracts import Request
from aura.core import ServiceError
from aura.rag.prompts.templates import ANSWER_SYSTEM
from .answers import Answer, validate_citations
from .context import evidence_payload

@traced('answer_generation')
async def query(pipeline,question,document_id=None):
    found=await pipeline.search(question,document_id=document_id); cs=found['chunks']
    if not cs: return {'answer':Answer(answer='Insufficient evidence.',insufficient_evidence=True,citations=[]),'evidence':[], 'retrieval':found}
    provider,model=pipeline.gateway.preferred_generation()
    if model not in pipeline.gateway.available.get(provider,[]): await pipeline.gateway.discover(provider)
    prompt=json.dumps({'question':question,'evidence':evidence_payload(cs)})
    usage=0
    for attempt in range(2):
        system=ANSWER_SYSTEM
        if attempt:
            system+=' Your previous response failed citation validation. Use short literal quotes copied exactly from the supplied chunk, including line breaks. Do not alter punctuation or join separate passages. Use only the supplied chunk IDs.'
        result=await pipeline.gateway.generate(provider,model,Request(prompt=prompt,max_tokens=1024),verify=True,schema=Answer,system=system)
        usage+=result.tokens
        answer=Answer.model_validate_json(result.text)
        try:
            with span('citation_validation'):
                validate_citations(answer,cs)
        except ServiceError as exc:
            if attempt or exc.code not in ('invalid_citation','missing_citations'):
                raise
            emit('citation_retry', error=exc.code, attempt=attempt+2)
            continue
        return {'answer':answer,'evidence':cs,'retrieval':found,'usage':usage,'generation_attempts':attempt+1,'support_validation':'identity_and_exact_quote_only'}
