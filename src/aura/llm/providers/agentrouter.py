"""AgentRouter inference through its supported OpenCode client."""
import asyncio
from aura.observability.events import traced, emit
import json
import os
import tempfile
from pathlib import Path

from aura.core import ServiceError


@traced('agentrouter_client')
async def generate(key: str, model: str, prompt: str, *, timeout: int = 90) -> tuple[str, int]:
    emit('agentrouter_connection', host='agentrouter.org', client='opencode', model=model)
    if not key:
        raise ServiceError('missing_credentials')
    config = {
        '$schema': 'https://opencode.ai/config.json',
        'providers': {
            'agentrouter': {
                'name': 'AgentRouter',
                'env': ['AGENTROUTER_API_KEY'],
                'package': '@opencode/ai/providers/openai-compatible',
                'settings': {'baseURL': 'https://agentrouter.org/v1'},
                'models': {model: {'name': model}},
            }
        },
    }
    with tempfile.TemporaryDirectory(prefix='aura-opencode-') as directory:
        path = Path(directory) / 'opencode.json'
        path.write_text(json.dumps(config))
        env = os.environ.copy()
        env.update(AGENTROUTER_API_KEY=key, OPENCODE_CONFIG=str(path), OPENCODE_DB=':memory:')
        try:
            process = await asyncio.create_subprocess_exec(
                'opencode', 'run', '--format', 'json',
                '--model', f'agentrouter/{model}', prompt,
                cwd=directory, env=env,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise ServiceError('opencode_not_installed') from None
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            raise
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise ServiceError('timeout') from None
    if process.returncode:
        error = stderr.decode('utf-8', 'replace').lower()
        if '401' in error or 'unauthorized' in error:
            raise ServiceError('http_401')
        if 'no available channel' in error or '无可用渠道' in error:
            raise ServiceError('model_unavailable')
        raise ServiceError('agentrouter_cli_failed')
    parts = []
    tokens = 0
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        part = event.get('part', {})
        if event.get('type') == 'text' and isinstance(part.get('text'), str):
            parts.append(part['text'])
        if event.get('type') == 'step_finish':
            tokens += part.get('tokens', {}).get('total', 0) or 0
    answer = ''.join(parts).strip()
    if not answer:
        raise ServiceError('empty_response')
    return answer, tokens
