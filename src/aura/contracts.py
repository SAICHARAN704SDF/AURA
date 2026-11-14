"""Public request, response, health, NLP and OCR contracts."""
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
