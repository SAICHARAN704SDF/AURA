"""Single-user workspace profile API. Project identifiers scope preferences, not authentication."""
from typing import Annotated
from fastapi import APIRouter, Path, Request

from aura.memory.profiles import Feedback, Profile
from aura.rag.api.routes import Search

router = APIRouter(prefix='/projects/{project}')
Project = Annotated[str, Path(pattern=r'^[a-zA-Z0-9_-]{1,64}$')]

@router.get('/profile')
async def read_profile(project: Project, request: Request):
    return request.app.state.rag.profiles.get(project)

@router.put('/profile')
async def write_profile(project: Project, body: Profile, request: Request):
    return request.app.state.rag.profiles.save(project, body)

@router.put('/feedback')
async def record_feedback(project: Project, body: Feedback, request: Request):
    pipeline = request.app.state.rag
    pipeline.document(body.document_id)
    return pipeline.profiles.vote(project, body)

@router.post('/search')
async def search(project: Project, body: Search, request: Request):
    return await request.app.state.rag.search(body.question,body.top_k,body.document_id,project_id=project)
