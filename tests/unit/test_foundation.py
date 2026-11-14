import asyncio
import httpx
import pytest
from pydantic import ValidationError
from aura.core import Settings, ServiceError
from aura.contracts import Request, UnavailableOCR
from aura.llm.transport import Transport
from aura.llm.gateway import Gateway

def run(c): return asyncio.run(c)
def settings(**kw): return Settings(_env_file=None,**kw)
def test_config():
    with pytest.raises(ValidationError): settings(concurrency=0)
def test_request():
    with pytest.raises(ValidationError): Request(prompt='')
def test_secrets(): assert 'hidden-key' not in repr(settings(groq_api_key='hidden-key'))
def test_missing():
    g=Gateway(settings(),Transport(settings()))
    with pytest.raises(ServiceError,match='missing_credentials'): g.headers('groq')
def test_invalid_model():
    g=Gateway(settings(),Transport(settings()))
    with pytest.raises(ServiceError,match='invalid_model'): run(g.generate('groq','unknown',Request(prompt='test')))
def test_no_route():
    g=Gateway(settings(),Transport(settings()))
    with pytest.raises(ServiceError,match='no_verified_route'): run(g.route(Request(prompt='test'),[]))
def test_ocr():
    with pytest.raises(ServiceError,match='endpoint_not_verified'): run(UnavailableOCR().extract(b'x'))
@pytest.mark.parametrize('code',[401,402,429,503])
def test_http_errors(code):
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(code,headers={'retry-after':'0'}))) as c:
            with pytest.raises(ServiceError,match=f'http_{code}'): await Transport(settings(),c).request('GET','https://example.com')
    run(check())
def test_timeout():
    def fail(r): raise httpx.ReadTimeout('secret')
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as c:
            with pytest.raises(ServiceError,match='timeout'): await Transport(settings(),c).request('GET','https://example.com')
    run(check())
def test_memory():
    s=settings(); s.max_rss_mb=0
    with pytest.raises(ServiceError,match='memory_limit'): run(Transport(s).request('GET','https://example.com'))

def test_structured_validation():
    from pydantic import BaseModel
    class Expected(BaseModel):
        ok: bool
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':'{"wrong":1}'}}]}))) as c:
            g=Gateway(settings(groq_api_key='test'),Transport(settings(),c))
            g.available['groq']=['openai/gpt-oss-120b']
            with pytest.raises(ServiceError,match='invalid_structured_output'):
                await g.generate('groq','openai/gpt-oss-120b',Request(prompt='test'),verify=True,schema=Expected)
            assert not g.verified
    run(check())

def test_fallback():
    async def check():
        g=Gateway(settings(),Transport(settings()))
        g.verified={('groq','openai/gpt-oss-120b'),('gemini','gemini-2.5-flash')}
        from aura.contracts import Result
        async def generate(p,m,r,**kw):
            if p=='groq': raise ServiceError('http_429')
            return Result(text='ok',provider=p,model=m)
        g.generate=generate
        result=await g.for_capability('text',Request(prompt='test'))
        assert result.provider=='gemini'
        await g.transport.close()
    run(check())

def test_api(tmp_path):
    from fastapi.testclient import TestClient
    from aura.api import create_app
    with TestClient(create_app(settings().model_copy(update={'data_dir':str(tmp_path)}))) as client:
        assert client.get('/health').json()['status']=='unverified'
        assert client.get('/models').json()['inference_verified']==[]
        assert client.get('/providers/status').status_code==200

def test_hf_payload_and_credit_failure():
    import json
    async def check():
        def handler(r):
            body=json.loads(r.content)
            assert body['max_tokens']==64
            assert 'max_completion_tokens' not in body
            return httpx.Response(402,json={'error':'credits exhausted'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            g=Gateway(settings(hf_token='test'),Transport(settings(),c))
            g.available['huggingface']=['Qwen/Qwen3-14B']
            with pytest.raises(ServiceError,match='http_402'):
                await g.generate('huggingface','Qwen/Qwen3-14B',Request(prompt='test',max_tokens=64),verify=True)
            assert not g.verified
    run(check())
