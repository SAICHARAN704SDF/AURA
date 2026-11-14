"""Typed workflow API; execution runs in background asyncio tasks."""
import asyncio
from typing import Any
from fastapi import APIRouter,Request,Query
from pydantic import BaseModel,Field
from aura.agents.contracts import GoalInput,Plan,AGENTS
router=APIRouter()
class Created(BaseModel):
    id:str
    project_id:str
class WorkflowInput(BaseModel):
    goal_id:str
    project_id:str
    plan:Plan | None=None
class WorkflowResponse(BaseModel):
    id:str
    project_id:str
    goal_id:str
    state:str
    plan:dict | None
    tasks:dict
    llm_calls:int
    tool_calls:int
    tokens:int
    elapsed:float
    report:dict | None
    error:str | None
class GoalResponse(GoalInput):pass
class Events(BaseModel):
    events:list[dict[str,Any]]
class Report(BaseModel):
    state:str
    report:dict | None
class Catalog(BaseModel):
    items:list[dict[str,Any]]
def engine(r):return r.app.state.engine
@router.post('/goals',response_model=Created)
async def goal(body:GoalInput,request:Request):
    for id in body.document_ids:request.app.state.rag.document(id)
    id=engine(request).memory.create_goal(body);return Created(id=id,project_id=body.project_id)
@router.get('/goals/{id}',response_model=GoalResponse)
async def get_goal(id:str,project_id:str,request:Request):return engine(request).memory.goal(id,project_id)
@router.post('/workflows',response_model=Created)
async def workflow(body:WorkflowInput,request:Request):
    id=engine(request).memory.create(body.goal_id,body.project_id,body.plan.model_dump() if body.plan else None)
    return Created(id=id,project_id=body.project_id)
@router.get('/workflows/{id}',response_model=WorkflowResponse)
@router.get('/workflows/{id}/status',response_model=WorkflowResponse)
async def get_workflow(id:str,project_id:str,request:Request):return engine(request).memory.get(id,project_id)
@router.post('/workflows/{id}/execute',response_model=WorkflowResponse,status_code=202)
async def execute(id:str,project_id:str,request:Request):
    e=engine(request);w=e.memory.get(id,project_id)
    if id not in e.running and id not in request.app.state.jobs:
        task=asyncio.create_task(e.execute(id,project_id));request.app.state.jobs[id]=task
        task.add_done_callback(lambda _:request.app.state.jobs.pop(id,None))
    return w
@router.post('/workflows/{id}/cancel',response_model=WorkflowResponse)
async def cancel(id:str,project_id:str,request:Request):return engine(request).cancel(id,project_id)
@router.get('/workflows/{id}/events',response_model=Events)
async def events(id:str,project_id:str,request:Request,after:int=Query(default=0,ge=0)):
    return Events(events=engine(request).memory.events(id,project_id,after))
@router.get('/workflows/{id}/report',response_model=Report)
async def report(id:str,project_id:str,request:Request):
    w=engine(request).memory.get(id,project_id);return Report(state=w['state'],report=w['report'])
@router.get('/agents',response_model=Catalog)
async def agents():return Catalog(items=[a.model_dump() for a in AGENTS.values()])
@router.get('/tools',response_model=Catalog)
async def tools(request:Request):return Catalog(items=engine(request).dispatcher.catalog())
