"""Provider adapters, discovery, verified model registry and routing."""
from aura.observability.events import traced, emit, span
import json
from pydantic import BaseModel, ValidationError
from aura.core import Settings, ServiceError
from aura.contracts import Request, Result, Status
from .transport import Transport
from .registry import candidates
from .providers.agentrouter import generate as opencode_generate

class Gateway:
    def __init__(self, settings: Settings, transport: Transport):
        self.settings, self.transport = settings, transport
        self.keys = {'groq': settings.groq_api_key, 'gemini': settings.gemini_api_key,
                     'agentrouter': settings.agentrouter_api_key,
                     'huggingface': settings.hf_token, 'cloudflare': settings.cloudflare_api_token}
        self.status = {p: Status(configured=bool(k.get_secret_value())) for p,k in self.keys.items()}
        self.available: dict[str, list[str]] = {}
        self.verified: set[tuple[str,str]] = set()
        self.usage: dict[str,int] = {}
        self.base = {'groq':'https://api.groq.com/openai/v1', 'gemini':'https://generativelanguage.googleapis.com/v1beta',
                     'huggingface':'https://router.huggingface.co/v1',
                     'cloudflare':f'https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/ai'}

    def headers(self, provider: str) -> dict:
        if provider not in self.keys: raise ServiceError('invalid_provider')
        key = self.keys[provider].get_secret_value()
        if not key: raise ServiceError('missing_credentials')
        return {'x-goog-api-key':key} if provider == 'gemini' else {'Authorization':f'Bearer {key}'}

    async def discover(self, provider: str) -> list[str]:
        state = self.status[provider]
        if provider == 'agentrouter':
            # OpenCode is the supported client. The model is verified by inference,
            # since AgentRouter rejects direct model-list HTTP requests.
            models = [self.settings.agentrouter_model] if state.configured else []
            self.available[provider] = models
            return models
        try:
            suffix = '/models/search' if provider == 'cloudflare' else '/models'
            data = await self.transport.request('GET', self.base[provider]+suffix, headers=self.headers(provider))
            state.reachable = state.authenticated = True
            rows = data.get('models', data.get('data', data.get('result', [])))
            models = [r.get('id',r.get('name','')).removeprefix('models/') for r in rows]
            self.available[provider] = models
            state.error = None
            return models
        except ServiceError as exc:
            state.error = exc.code
            state.authenticated = False
            state.reachable = exc.code.startswith('http_')
            return []

    @traced('llm')
    async def generate(self, provider: str, model: str, request: Request, *, verify: bool=False, schema: type[BaseModel] | None=None, system: str | None=None) -> Result:
        emit('model_selected', provider=provider, model=model, max_output_tokens=request.max_tokens)
        if (provider,model) not in candidates('text'): raise ServiceError('invalid_model')
        if model not in self.available.get(provider, []): raise ServiceError('invalid_model')
        if not verify and (provider,model) not in self.verified: raise ServiceError('model_not_verified')
        # Cloudflare generation is excluded; HF must be explicitly verified before use.
        if provider not in ('groq','gemini','huggingface','agentrouter'): raise ServiceError('generation_disabled_cost_policy')
        if provider == 'agentrouter':
            instruction = system or ''
            if schema:
                instruction += '\nReturn only valid JSON matching this schema: ' + json.dumps(schema.model_json_schema())
            prompt = f'{instruction}\n\n{request.prompt}\n\nKeep the response within {request.max_tokens} tokens.'
            text, tokens = await opencode_generate(self.headers(provider)['Authorization'].removeprefix('Bearer '), model, prompt)
            self.status[provider].reachable = self.status[provider].authenticated = True
        elif provider == 'gemini':
            body = {'contents':[{'parts':[{'text':request.prompt}]}], 'generationConfig':{'maxOutputTokens':request.max_tokens}}
            if schema: body['generationConfig'].update(responseMimeType='application/json', responseSchema=schema.model_json_schema())
            data = await self.transport.request('POST',self.base[provider]+f'/models/{model}:generateContent',headers=self.headers(provider),json=body)
            try: text = ''.join(p.get('text','') for p in data['candidates'][0]['content']['parts'])
            except (KeyError,IndexError,TypeError): raise ServiceError('invalid_response') from None
            tokens = data.get('usageMetadata',{}).get('totalTokenCount',0)
        else:
            body = {'model':model,'messages':[{'role':'user','content':request.prompt}],'max_completion_tokens':request.max_tokens}
            if provider == 'groq' and model.startswith('openai/gpt-oss'): body['reasoning_effort']='low'
            if system: body['messages'].insert(0, {'role':'system','content':system})
            if provider == 'huggingface': body['max_tokens'] = body.pop('max_completion_tokens')
            if schema: body['response_format']={'type':'json_object'}; body['messages'][-1]['content'] += '\nReturn JSON matching: '+json.dumps(schema.model_json_schema())
            data = await self.transport.request('POST',self.base[provider]+'/chat/completions',headers=self.headers(provider),json=body)
            try: text = data['choices'][0]['message']['content']
            except (KeyError,IndexError,TypeError): raise ServiceError('invalid_response') from None
            tokens = data.get('usage',{}).get('total_tokens',0)
        if not isinstance(text,str) or not text.strip(): raise ServiceError('empty_response')
        self.usage[provider] = self.usage.get(provider,0)+tokens
        if schema:
            try: schema.model_validate_json(text)
            except ValidationError: raise ServiceError('invalid_structured_output') from None
        self.verified.add((provider,model))
        self.status[provider].inference_verified = True
        emit('token_usage', 'completed', provider=provider, model=model, tokens=tokens)
        return Result(text=text,model=model,provider=provider,tokens=tokens)

    def preferred_generation(self) -> tuple[str, str]:
        if self.settings.aura_llm_provider == 'agentrouter':
            return 'agentrouter', self.settings.agentrouter_model
        return 'groq', 'openai/gpt-oss-120b'

    async def route(self, request: Request, candidates: list[tuple[str,str]], schema: type[BaseModel] | None=None) -> Result:
        for provider,model in candidates:
            if (provider,model) not in self.verified: continue
            try: return await self.generate(provider,model,request,schema=schema)
            except ServiceError as exc:
                if exc.code not in ('http_429','http_503','timeout','rate_limited','connection_error'): raise
        raise ServiceError('no_verified_route')

    async def for_capability(self, capability: str, request: Request, schema: type[BaseModel] | None=None) -> Result:
        return await self.route(request, candidates(capability), schema)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts or len(texts)>16 or any(len(t)>2000 for t in texts): raise ServiceError('embedding_input_limit')
        model='@cf/baai/bge-m3'
        data=await self.transport.request('POST',self.base['cloudflare']+'/run/'+model,headers=self.headers('cloudflare'),json={'text':texts})
        try: vectors=data['result']['data']
        except (KeyError,TypeError): raise ServiceError('invalid_response') from None
        if len(vectors)!=len(texts) or any(not v for v in vectors): raise ServiceError('invalid_vectors')
        self.status['cloudflare'].inference_verified=True
        self.verified.add(('cloudflare',model))
        return vectors

    @traced('reranking')
    async def rerank(self, query: str, texts: list[str]) -> list[dict]:
        if not query or not texts or len(texts)>10 or any(len(t)>2000 for t in texts): raise ServiceError('rerank_input_limit')
        data=await self.transport.request('POST',self.base['cloudflare']+'/run/@cf/baai/bge-reranker-base',headers=self.headers('cloudflare'),json={'query':query,'contexts':[{'text':t} for t in texts]})
        result=data.get('result',{}).get('response')
        if not isinstance(result,list): raise ServiceError('invalid_response')
        return result
