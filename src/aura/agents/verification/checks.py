"""Independent provenance and numeric verification; semantic support is explicit."""
import re
from aura.agents.contracts import Verification,TaskOutput
from aura.agents.tools.dispatcher import OPS

def verify(outputs,observations,goal):
    chunks={c['id']:c for o in observations if o['tool']=='rag_search' for c in o['data']['chunks']}
    calls={o['call_id']:o for o in observations}
    criteria=[];evidence=[];comparisons=[]
    for raw in outputs:
        out=TaskOutput.model_validate(raw);evidence+=out.evidence;comparisons+=out.comparisons
    for e in evidence:
        c=chunks.get(e.chunk_id)
        ok=c is not None and c['document_id']==e.document_id and e.document_id in goal.document_ids and e.quote in c['text']
        criteria.append({'criterion':'citation_and_quote','outcome':'PASS' if ok else 'FAIL'})
    for c in comparisons:
        audit=calls.get(c.tool_call_id)
        quotes=[e.quote for e in evidence]
        numbers=lambda q:[float(n) for n in re.findall(r'(?<!\w)-?\d+(?:\.\d+)?',q)]
        supported=c.measurement_quote in quotes and c.requirement_quote in quotes and c.measurement in numbers(c.measurement_quote) and c.requirement in numbers(c.requirement_quote)
        unit_ok=bool(c.unit.strip()) and c.unit.lower() in c.measurement_quote.lower() and c.unit.lower() in c.requirement_quote.lower()
        expected=OPS[c.operator](c.measurement,c.requirement)
        ok=bool(audit and audit['tool']=='calculator' and audit['data']=={'left':c.measurement,'right':c.requirement,'operation':c.operator,'result':expected})
        criteria.append({'criterion':'numeric_comparison','outcome':'PASS' if supported and unit_ok and ok else 'FAIL'})
    if not evidence:criteria.append({'criterion':'evidence_required','outcome':'FAIL'})
    for criterion in goal.acceptance:
        # Free-form criteria need semantic judgment; deterministic checks do not claim entailment.
        numeric=any(w in criterion.lower() for w in ('measurement','compare','comparison'))
        citation=any(w in criterion.lower() for w in ('citation','quote','evidence reference'))
        outcome='PASS' if (numeric and comparisons or citation and evidence) else 'INCONCLUSIVE'
        criteria.append({'criterion':criterion,'outcome':outcome})
    outcome='FAIL' if any(c['outcome']=='FAIL' for c in criteria) else 'INCONCLUSIVE' if any(c['outcome']=='INCONCLUSIVE' for c in criteria) else 'PASS'
    return Verification(outcome=outcome,criteria=criteria,limitations=['Exact quotes and explicit numeric relations verified; general semantic entailment is not established.'])
