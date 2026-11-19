import asyncio

from pydantic import BaseModel

from aura.contracts import Request
from aura.core import Settings
from aura.llm.gateway import Gateway
from aura.llm.transport import Transport


def test_agentrouter_selected_and_structured(monkeypatch):
    class Answer(BaseModel):
        answer: str

    captured = {}

    async def fake_cli(key, model, prompt):
        captured.update(key=key, model=model, prompt=prompt)
        return '{"answer":"OK"}', 12

    monkeypatch.setattr('aura.llm.gateway.opencode_generate', fake_cli)

    async def check():
        settings = Settings(_env_file=None, agentrouter_api_key='test-key', aura_llm_provider='agentrouter')
        transport = Transport(settings)
        gateway = Gateway(settings, transport)
        try:
            assert gateway.preferred_generation() == ('agentrouter', 'gpt-5.6-sol')
            assert await gateway.discover('agentrouter') == ['gpt-5.6-sol']
            result = await gateway.generate('agentrouter', 'gpt-5.6-sol', Request(prompt='Reply OK.', max_tokens=32), verify=True, schema=Answer)
            assert Answer.model_validate_json(result.text).answer == 'OK'
            assert result.tokens == 12
            assert captured['key'] == 'test-key'
            assert 'test-key' not in captured['prompt']
            assert 'answer' in captured['prompt']
        finally:
            await transport.close()

    asyncio.run(check())
