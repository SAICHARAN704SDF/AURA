"""Boundary, persistence and isolation checks added during the full audit."""
import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from aura.core import Settings,ServiceError
from aura.api import create_app
from aura.rag.ingestion.documents import load
from aura.rag.chunking.chunker import chunks
from aura.rag.pipeline import Pipeline
from aura.rag.embeddings.cache import Embeddings

class Fake:
    calls=0
    async def embed(self,texts):
        self.calls+=1
        return [[1.0]+[0.0]*1023 for _ in texts]
    async def rerank(self,q,texts):return [{'id':i,'score':1/(i+1)} for i in range(len(texts))]

@pytest.mark.parametrize('name,data,code',[
 ('a.txt',b'','invalid_file_size'),('a.txt',b'a'*(5*1024*1024+1),'invalid_file_size'),
 ('../a.txt',b'x','invalid_filename'),('a\\b.txt',b'x','invalid_filename'),
 ('a.txt',b'\xff','invalid_encoding'),('a.txt',b'hello\x00world','invalid_text'),
 ('a.csv',b'a,b\n1','invalid_csv'),('a.csv',b'"unterminated','invalid_csv'),
 ('a.pdf',b'not PDF','invalid_pdf'),('a.exe',b'no','unsupported_file_type')])
def test_reject_documents(name,data,code):
    with pytest.raises(ServiceError,match=code):load(name,data)

@pytest.mark.parametrize('size,overlap',[(99,0),(1801,0),(100,-1),(100,100)])
def test_chunk_boundaries(size,overlap):
    with pytest.raises(ServiceError,match='invalid_chunk_config'):chunks(load('a.txt',b'text'),size,overlap)

@pytest.mark.parametrize('text',['a'*3900,('line\n'*400),('科学研究🙂 '*500),'   \n  '])
def test_chunk_coverage_and_offsets(text):
    doc=load('unicode.txt',text.encode());result=chunks(doc)
    covered=set()
    for c in result:
        assert c.text==text[c.start:c.end]
        assert 0<len(c.text)<=1200
        covered.update(range(c.start,c.end))
    assert all(i in covered for i,c in enumerate(text) if not c.isspace())

@pytest.mark.parametrize('vector',[[0.0]*1023,[float('nan')]*1024,[float('inf')]*1024])
def test_bad_vectors(tmp_path,vector):
    cache=Embeddings(Fake(),tmp_path/'cache.sqlite')
    try:
        with pytest.raises(ServiceError,match='embedding_dimension_mismatch'):cache.validate(vector)
    finally:cache.close()

def test_batch_cache_and_restart(tmp_path):
    async def run():
        fake=Fake();path=tmp_path/'cache.sqlite';e=Embeddings(fake,path)
        texts=[f'text {i}' for i in range(17)]
        first=await e.embed(texts);assert fake.calls==2
        assert await e.embed(texts)==first and fake.calls==2
        e.close();e=Embeddings(fake,path)
        assert await e.embed(texts)==first and fake.calls==2;e.close()
    asyncio.run(run())

def test_scope_and_mutation_recovery(tmp_path):
    async def run():
        p=Pipeline(Fake(),tmp_path)
        a=(await p.ingest('a.txt',b'Alpha telescope blue mirror.'))['document']
        b=(await p.ingest('b.txt',b'Beta telescope red mirror.'))['document']
        result=await p.search('mirror',document_id=a.id)
        assert {c.document_id for c in result['chunks']}=={a.id}
        with p.db:p.db.execute('INSERT INTO mutations VALUES (?)',(b.id,))
        p.close();p=Pipeline(Fake(),tmp_path)
        assert p.document(a.id)
        with pytest.raises(ServiceError,match='document_not_found'):p.document(b.id)
        assert not p.store.all(b.id);p.close()
    asyncio.run(run())

@pytest.mark.parametrize('path,body',[
 ('/retrieval/search',{'question':''}),('/retrieval/search',{'question':'x','top_k':6}),
 ('/nlp/analyze',{'text':''}),('/nlp/similarity',{'first':'x','second':''}),
 ('/goals',{'project_id':'../escape','goal':'x'}),
 ('/goals',{'project_id':'p','goal':'x','budget':{'llm_calls':31}})])
def test_api_invalid_payloads(tmp_path,path,body):
    with TestClient(create_app(Settings(_env_file=None,data_dir=str(tmp_path)))) as c:
        assert c.post(path,json=body).status_code==422

def test_static_paths_and_missing_records(tmp_path):
    with TestClient(create_app(Settings(_env_file=None,data_dir=str(tmp_path)))) as c:
        assert c.get('/assets/subjects.js').status_code==200
        assert c.get('/assets/%2e%2e/.env').status_code in (400,404)
        assert c.get('/documents/missing').status_code==404
        assert c.get('/workflows/missing?project_id=p').status_code==404
        assert c.get('/monitor/events?after=-1').status_code==422
        assert c.post('/documents/upload?strategy=bad',files={'file':('a.txt',b'text')}).status_code==422
