"""NLP analysis, similarity, and status endpoints."""
import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class Pair(BaseModel):
    first: str = Field(min_length=1, max_length=2000)
    second: str = Field(min_length=1, max_length=2000)


@router.post('/nlp/analyze')
async def analyze(body: Text, request: Request):
    return await asyncio.to_thread(request.app.state.nlp.analyze, body.text)


@router.post('/nlp/similarity')
async def similarity(body: Pair, request: Request):
    return await request.app.state.nlp.similarity(body.first, body.second)


@router.get('/nlp/status')
async def status(request: Request):
    return request.app.state.nlp.status()
