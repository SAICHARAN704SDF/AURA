"""
FILE: backend/src/aura/contracts.py
PURPOSE: Define bounded requests, results, status and integration protocols.
MAIN RESPONSIBILITY: Provider Data Contracts.
INPUTS: Prompt text, token limits and provider response fields.
OUTPUTS: Pydantic records and protocol interfaces.
IMPORTANT FUNCTIONS / CLASSES: Request, Result, Status, OCRPage, OCRProvider, NLPProvider, UnavailableOCR.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: backend/src/aura/llm/gateway.py, backend/src/aura/rag/generation/generator.py, backend/src/aura/orchestration/workflow/engine.py.
PRESENTATION EXPLANATION: "These contracts define the data boundary; a protocol or unavailable adapter is not a working integration."
"""
# PRESENTATION SECTION: PROVIDER DATA CONTRACTS
from typing import Protocol
from pydantic import BaseModel, Field, ConfigDict

class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    prompt: str = Field(min_length=1, max_length=12000)
    max_tokens: int = Field(default=128, ge=1, le=4096)

class Result(BaseModel):
    text: str
    model: str
    provider: str
    tokens: int = Field(default=0, ge=0)

class Status(BaseModel):
    configured: bool = False
    reachable: bool = False
    authenticated: bool = False
    inference_verified: bool = False
    error: str | None = None

class OCRPage(BaseModel):
    text: str
    page: int = Field(ge=1)
    model: str

class OCRProvider(Protocol):
    async def extract(self, image: bytes) -> OCRPage: ...

class NLPProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def rerank(self, query: str, texts: list[str]) -> list[dict]: ...

class UnavailableOCR:
    async def extract(self, image: bytes) -> OCRPage:
        from .core import ServiceError
        raise ServiceError('ocr_endpoint_not_verified')
