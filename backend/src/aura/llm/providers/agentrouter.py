"""
FILE: backend/src/aura/llm/providers/agentrouter.py
PURPOSE: Invoke configured AgentRouter generation through OpenCode.
MAIN RESPONSIBILITY: Agentrouter Adapter.
INPUTS: Secret key, model identifier, prompt and timeout.
OUTPUTS: Generated text and reported token count.
IMPORTANT FUNCTIONS / CLASSES: generate.
CONNECTED MODULES: aura.observability.events, aura.core.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "The optional adapter uses an isolated temporary directory and passes the key through the environment."
"""
# PRESENTATION SECTION: AGENTROUTER ADAPTER
import asyncio
from aura.observability.events import traced, emit
import json
import os
import tempfile
from pathlib import Path

from aura.core import ServiceError


@traced('agentrouter_client')
async def generate(key: str, model: str, prompt: str, *, timeout: int = 90) -> tuple[str, int]:
    """Purpose: AgentRouter integration.
    
    Inputs: API key, model, prompt and timeout.
    Process and rationale: Run OpenCode in an isolated directory, pass the credential in its environment and parse NDJSON output; kill cancelled/timed-out child processes.
    Returns: Text and reported token count tuple.
    """
    emit('agentrouter_connection', host='agentrouter.org', client='opencode', model=model)
    if not key:
        raise ServiceError('missing_credentials')
    config = {
        '$schema': 'https://opencode.ai/config.json',
        'permission': {'*':'deny'},
        'provider': {
            'agentrouter': {
                'name': 'AgentRouter',
                'env': ['AGENTROUTER_API_KEY'],
                'npm': '@ai-sdk/openai-compatible',
                'options': {'baseURL': 'https://agentrouter.org/v1','apiKey':'{env:AGENTROUTER_API_KEY}'},
                'models': {model: {'name': model}},
            }
        },
    }
    with tempfile.TemporaryDirectory(prefix='aura-opencode-') as directory:
        path = Path(directory) / 'opencode.json'
        path.write_text(json.dumps(config))
        env = {name:os.environ[name] for name in ('PATH','LANG','SSL_CERT_FILE') if name in os.environ}
        env.update(HOME=directory, XDG_CONFIG_HOME=directory+'/config', XDG_DATA_HOME=directory+'/data',
                   XDG_STATE_HOME=directory+'/state', XDG_CACHE_HOME=directory+'/cache')
        env.update(AGENTROUTER_API_KEY=key, OPENCODE_CONFIG=str(path), OPENCODE_DB=':memory:')
        try:
            process = await asyncio.create_subprocess_exec(
                'opencode', 'run', '--pure', '--format', 'json',
                '--model', f'agentrouter/{model}', '--', prompt,
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
