"""Exercise the real adapter with a fake process, never a provider request."""
import asyncio
import json
from pathlib import Path
import pytest
from aura.core import ServiceError
from aura.llm.providers.agentrouter import generate


def test_cli_protocol_and_cleanup(monkeypatch):
    captured = {}
    class Process:
        returncode = 0
        async def communicate(self):
            return (b'noise\n{"type":"text","part":{"text":"OK"}}\n'
                    b'{"type":"step_finish","part":{"tokens":{"total":12}}}\n', b'')
    async def spawn(*args, **kwargs):
        captured.update(args=args, **kwargs)
        config = json.loads(Path(kwargs['env']['OPENCODE_CONFIG']).read_text())
        provider = config['provider']['agentrouter']
        assert config['permission']=={'*':'deny'}
        assert 'GROQ_API_KEY' not in kwargs['env']
        assert provider['options']['baseURL'] == 'https://agentrouter.org/v1'
        assert 'dummy-secret' not in json.dumps(config)
        assert kwargs['env']['AGENTROUTER_API_KEY'] == 'dummy-secret'
        return Process()
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    assert asyncio.run(generate('dummy-secret', 'gpt-5.6-sol', 'Hello')) == ('OK', 12)
    assert captured['args'] == ('opencode', 'run', '--pure', '--format', 'json', '--model', 'agentrouter/gpt-5.6-sol', '--', 'Hello')
    assert not Path(captured['cwd']).exists()


@pytest.mark.parametrize('stderr,code', [(b'401 secret', 'http_401'), (b'no available channel', 'model_unavailable'), (b'private failure', 'agentrouter_cli_failed')])
def test_cli_errors_are_sanitized(monkeypatch, stderr, code):
    class Process:
        returncode = 1
        async def communicate(self): return b'', stderr
    async def spawn(*args, **kwargs): return Process()
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    with pytest.raises(ServiceError, match='^'+code+'$'):
        asyncio.run(generate('dummy-secret', 'gpt-5.6-sol', 'Hello'))


def test_cancel_kills_cli(monkeypatch):
    async def check():
        started=asyncio.Event()
        class Process:
            returncode=None
            killed=False
            async def communicate(self):
                if self.killed:return b'',b''
                started.set()
                await asyncio.Event().wait()
            def kill(self):self.killed=True;self.returncode=-9
        process=Process()
        async def spawn(*args,**kwargs):return process
        monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn)
        task=asyncio.create_task(generate('dummy-secret','gpt-5.6-sol','test'))
        await started.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert process.killed
    asyncio.run(check())
