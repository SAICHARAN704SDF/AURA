"""Environment-based application settings."""
from pydantic import SecretStr, Field
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', hide_input_in_errors=True)
    groq_api_key: SecretStr = SecretStr('')
    gemini_api_key: SecretStr = SecretStr('')
    hf_token: SecretStr = SecretStr('')
    cloudflare_api_token: SecretStr = SecretStr('')
    cloudflare_account_id: str = ''
    agentrouter_api_key: SecretStr = SecretStr('')
    aura_llm_provider: Literal['groq','agentrouter'] = 'groq'
    agentrouter_model: str = 'gpt-5.6-sol'
    groq_model: str = 'openai/gpt-oss-20b'
    data_dir: str = 'data'
    qdrant_url: str | None = None
    timeout: float = Field(default=30, gt=0, le=120)
    concurrency: int = Field(default=2, ge=1, le=4)
    max_rss_mb: int = Field(default=512, ge=64)
