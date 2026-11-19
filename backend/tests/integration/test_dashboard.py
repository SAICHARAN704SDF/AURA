import json
import time
from fastapi.testclient import TestClient
from aura.api import create_app
from aura.core import Settings
from aura.contracts import Result
from aura.observability.events import EventBus

class Provider:
    available={'groq':['openai/gpt-oss-120b']}
    def preferred_generation(self): return 'groq','openai/gpt-oss-120b'
    async def embed(self,texts):return [[1.0]+[0.0]*1023 for _ in texts]
    async def rerank(self,question,texts):return [{'id':i,'score':1/(i+1)} for i in range(len(texts))]
    async def generate(self,provider,model,request,**kwargs):
        if kwargs.get('schema').__name__ in ('ClaimReview','CompleteClaimReview'):
            return Result(text=json.dumps({'judgments':[{'index':0,'outcome':'supported','reason':'Test fixture support.'}]}),model=model,provider=provider,tokens=6)
        evidence=json.loads(request.prompt)['evidence'][0]
        return Result(text=json.dumps({'answer':'Blue mirrors reflect light.','insufficient_evidence':False,
            'citations':[{'chunk_id':evidence['chunk_id'],'quote':'Blue mirrors'}]}),model=model,provider=provider,tokens=12)


def test_dashboard_upload_query_trace_and_errors(tmp_path):
    with TestClient(create_app(Settings(_env_file=None,data_dir=str(tmp_path)))) as client:
        provider=Provider();client.app.state.rag.gateway=provider;client.app.state.rag.embedding.gateway=provider
        assert client.get('/').status_code==200
        assert 'Watch the steps' in client.get('/').text
        assert client.get('/assets/app.js').status_code==200
        assert client.get('/assets/subjects.js').status_code==200
        assert 'id="stationMap"' in client.get('/').text
        status=client.get('/monitor/status').json()
        assert status['tunnel']['state']=='unverified' and status['credits']=='unknown'
        headers={'X-Aura-Trace':'test-upload'}
        r=client.post('/documents/upload',headers=headers,files={'file':('test.txt',b'Blue mirrors reflect light. SECRET_SOURCE_TEXT')})
        assert r.status_code==200
        document=r.json()['document']['id']
        r=client.post('/rag/query',headers=headers,json={'question':'What reflects light?','document_id':document})
        assert r.status_code==200 and r.json()['answer']['citations']
        rows=client.get('/monitor/events').json()['events']
        stages={r['stage'] for r in rows}
        assert {'server_request','ingestion','parsing','chunking','embeddings','embedding_cache','vector_storage',
                'retrieval','dense_search','lexical_search','bm25_fusion','answer_generation','context_assembly',
                'embedding_request','embedding_validation'} <= stages
        assert all(r['trace_id']=='test-upload' for r in rows)
        assert 'SECRET_SOURCE_TEXT' not in json.dumps(rows)
        assert any(r['stage']=='embedding_cache' and r['hits']>=0 for r in rows)
        cursor=rows[-1]['sequence']
        assert client.get(f'/monitor/events?after={cursor}').json()['events']==[]
        bad=client.post('/documents/upload',headers=headers,files={'file':('bad.exe',b'no')})
        assert bad.status_code==415
        rows=client.get(f'/monitor/events?after={cursor}').json()['events']
        assert any(e['status']=='failed' for e in rows)


def test_workflow_telemetry_scoping_and_history(tmp_path):
    from aura.agents.contracts import TaskOutput
    with TestClient(create_app(Settings(_env_file=None,data_dir=str(tmp_path)))) as client:
        async def worker(*args):return TaskOutput(summary='No supporting evidence.')
        client.app.state.engine.worker=worker
        gid=client.post('/goals',json={'project_id':'test','goal':'Test'}).json()['id']
        wid=client.post('/workflows',json={'project_id':'test','goal_id':gid,'plan':{'tasks':[
            {'id':'one','description':'Test','agent':'analysis','tools':[],'acceptance':['evidence']}]}}).json()['id']
        assert client.post(f'/workflows/{wid}/execute?project_id=test').status_code==202
        for _ in range(100):
            w=client.get(f'/workflows/{wid}?project_id=test').json()
            if w['state'] in ('COMPLETED','FAILED'):break
            time.sleep(.01)
        assert w['state']=='FAILED'
        rows=client.get('/monitor/events').json()['events']
        stages={r['stage'] for r in rows if r['trace_id']==wid}
        assert {'planning','task_wave','verification','workflow_event'}<=stages
        assert client.get('/monitor/workflows?project_id=other').json()==[]
        assert client.get('/monitor/workflows?project_id=test').json()[0]['id']==wid


def test_telemetry_buffer_is_bounded():
    bus=EventBus(capacity=2)
    for i in range(4):bus.publish({'value':i})
    assert len(bus.read()['events'])==2
    assert bus.read(after=1)['truncated']


def test_citation_retry_is_bounded_and_counts_usage(tmp_path):
    import asyncio
    from aura.rag.pipeline import Pipeline
    from aura.core import ServiceError
    import pytest
    class RetryProvider(Provider):
        calls=0
        always_invalid=False
        async def generate(self,provider,model,request,**kwargs):
            if kwargs.get('schema').__name__ in ('ClaimReview','CompleteClaimReview'):return await super().generate(provider,model,request,**kwargs)
            self.calls+=1
            good=await super().generate(provider,model,request,**kwargs)
            if self.calls==1 or self.always_invalid:
                body=json.loads(good.text);body['citations'][0]['quote']='Fabricated quote'
                return good.model_copy(update={'text':json.dumps(body)})
            assert 'previous response failed' in kwargs['system']
            return good
    async def check():
        provider=RetryProvider();pipeline=Pipeline(provider,tmp_path)
        try:
            await pipeline.ingest('test.txt',b'Blue mirrors reflect light.')
            result=await pipeline.query('What reflects light?')
            assert result['generation_attempts']==2 and result['usage']==30
            provider.calls=0;provider.always_invalid=True
            with pytest.raises(ServiceError,match='invalid_citation'):
                await pipeline.query('What reflects light?')
            assert provider.calls==2
        finally:pipeline.close()
    asyncio.run(check())
