"""Explicit model allowlist; discovery alone does not authorize inference."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Model:
    provider: str
    id: str
    capabilities: frozenset[str]

MODELS = [
    Model('agentrouter','gpt-5.6-sol',frozenset({'text','structured'})),
    Model('huggingface','Qwen/Qwen3-14B',frozenset({'text'})),
    Model('huggingface','meta-llama/Llama-3.1-8B-Instruct',frozenset({'text'})),
    Model('huggingface','openai/gpt-oss-20b',frozenset({'text'})),
    Model('groq','openai/gpt-oss-120b',frozenset({'text','structured'})),
    Model('gemini','gemini-3.8-flash',frozenset({'text','structured'})),
    Model('gemini','gemini-3.5-flash-lite',frozenset({'text','structured'})),
    Model('gemini','gemini-2.5-flash',frozenset({'text','structured'})),
    Model('gemini','gemini-2.0-flash',frozenset({'text','structured'})),
]

def candidates(capability: str) -> list[tuple[str,str]]:
    return [(m.provider,m.id) for m in MODELS if capability in m.capabilities]
