import asyncio
import pytest
from aura.agents.verification.claims import ClaimReview,Judgment,review
from aura.core import ServiceError


def test_claim_review_requires_complete_unique_coverage():
    async def missing(*args):return ClaimReview(judgments=[])
    with pytest.raises(ServiceError,match='incomplete_claim_review'):
        asyncio.run(review('A model uses attention.',['attention'],missing))


def test_unsupported_claim_fails_closed():
    async def unsupported(*args):
        return ClaimReview(judgments=[Judgment(index=0,outcome='unsupported',reason='Number absent.')])
    result=asyncio.run(review('Accuracy was 99 percent.',['Accuracy was measured.'],unsupported))
    assert result['outcome']=='INCONCLUSIVE'
    assert result['guarantee'] is False


def test_scanned_page_ocr_real():
    import pymupdf
    from aura.rag.ingestion.ocr import tessdata
    from aura.rag.ingestion.documents import load
    if tessdata() is None:pytest.skip('Install English OCR data with backend/scripts/setup_ocr.py')
    with pymupdf.open() as original:
        page=original.new_page(width=600,height=300)
        page.insert_text((40,80),'AURA research uses attention and retrieval.',fontsize=20)
        png=page.get_pixmap(matrix=pymupdf.Matrix(2,2)).tobytes('png')
    with pymupdf.open() as scanned:
        page=scanned.new_page(width=600,height=300);page.insert_image(page.rect,stream=png)
        doc=load('scan.pdf',scanned.tobytes())
    assert doc.pages[0].ocr_applied and not doc.pages[0].requires_ocr
    assert 'attention and retrieval' in doc.pages[0].text


def test_inline_citation_is_resolved_from_trusted_catalog():
    from aura.agents.worker import EvidenceDraft,materialize_draft
    draft=EvidenceDraft(summary='Supported [0].',evidence_indices=[],limitations=[])
    output=materialize_draft(draft,[{'document_id':'d','chunk_id':'c','quote':'Supported'}])
    assert output.summary=='Supported [Source 1].'
    assert output.evidence[0].quote=='Supported'
    with pytest.raises(ServiceError):
        materialize_draft(draft,[])


def test_finalize_withholds_unsupported_sentences(tmp_path,monkeypatch):
    from aura.agents.contracts import GoalInput,TaskOutput,Verification
    from aura.orchestration.workflow.persistence import Memory
    from aura.orchestration.workflow.engine import Engine
    from aura.orchestration.graph.nodes import finalize
    import aura.agents.verification.claims as claims
    import aura.orchestration.graph.nodes as nodes
    async def checked(*args):
        return {'outcome':'INCONCLUSIVE','claims':[{'claim':'Supported fact.','outcome':'supported','reason':'source'}, {'claim':'Invented fact.','outcome':'unsupported','reason':'absent'}]}
    monkeypatch.setattr(claims,'review',checked)
    monkeypatch.setattr(nodes,'verify',lambda *a:Verification(outcome='PASS',criteria=[],limitations=[]))
    m=Memory(tmp_path/'state.sqlite');goal=GoalInput(project_id='test',goal='report')
    gid=m.create_goal(goal);wid=m.create(gid,'test');w=m.get(wid,'test')
    w['plan']={'tasks':[{'id':'report','dependencies':[]}]}
    w['tasks']={'report':{'state':'COMPLETED','output':TaskOutput(summary='Supported fact. Invented fact.').model_dump()}}
    m.save(w,state='PLANNING');m.save(w,state='RUNNING')
    engine=Engine(object(),m,None)
    asyncio.run(finalize(engine,w,goal))
    assert w['state']=='COMPLETED'
    assert w['report']['results'][0]['summary']=='Supported fact.'
    assert w['report']['claim_reviews'][0]['draft_outcome']=='INCONCLUSIVE'
    m.close()


def test_direct_image_upload_uses_ocr(monkeypatch):
    import pymupdf
    from aura.rag.ingestion.documents import load
    import aura.rag.ingestion.ocr as ocr
    monkeypatch.setattr(ocr,'extract',lambda page:'Recognized image text.')
    with pymupdf.open() as pdf:
        page=pdf.new_page(width=100,height=100)
        image=page.get_pixmap().tobytes('png')
    doc=load('scan.png',image)
    assert doc.filename=='scan.png'
    assert doc.pages[0].ocr_applied
    assert doc.pages[0].text=='Recognized image text.'
    with pytest.raises(ServiceError,match='invalid_image'):
        load('bad.png',b'invalid image')
