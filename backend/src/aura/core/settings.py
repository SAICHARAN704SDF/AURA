"""
FILE: backend/src/aura/core/settings.py
PURPOSE: Load typed environment settings without exposing secret values.
MAIN RESPONSIBILITY: Configuration.
INPUTS: Environment variables and the local .env file.
OUTPUTS: Validated Settings instance.
IMPORTANT FUNCTIONS / CLASSES: Settings.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "Configuration selects providers and storage paths without putting credentials in source code."
"""
# PRESENTATION SECTION: CONFIGURATION
from pydantic import SecretStr, Field
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Validated runtime configuration loaded from environment and .env. SecretStr fields avoid accidental repr disclosure; the file is local and excluded from Git."""
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', hide_input_in_errors=True)
    groq_api_key: SecretStr = SecretStr('')
    gemini_api_key: SecretStr = SecretStr('')
    hf_token: SecretStr = SecretStr('')
    cloudflare_api_token: SecretStr = SecretStr('')
    cloudflare_account_id: str = ''
    agentrouter_api_key: SecretStr = SecretStr('')
    aura_llm_provider: Literal['groq','agentrouter','ollama','nvidia','openai_compatible'] = 'groq'
    compatible_base_url: str | None = None
    compatible_api_key: SecretStr = SecretStr('')
    compatible_model: str = ''
    agentrouter_model: str = 'gpt-5.6-sol'
    groq_model: str = 'openai/gpt-oss-20b'
    embedding_provider: Literal['cloudflare','local_minilm'] = 'cloudflare'
    data_dir: str = 'data'
    nlp_model: str = 'en_core_web_sm'
    nlp_domain_terms: dict[str, list[str]] = Field(default_factory=dict)
    qdrant_url: str | None = None
    timeout: float = Field(default=30, gt=0, le=120)
    concurrency: int = Field(default=2, ge=1, le=4)
    max_rss_mb: int = Field(default=512, ge=64)
