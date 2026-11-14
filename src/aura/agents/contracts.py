"""Typed agent contracts, policies, plans and state transitions."""
from enum import StrEnum
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator
from aura.core import ServiceError

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',hide_input_in_errors=True)
class State(StrEnum):
    PENDING='PENDING'; PLANNING='PLANNING'; RUNNING='RUNNING'; WAITING='WAITING'; VERIFYING='VERIFYING'; COMPLETED='COMPLETED'; FAILED='FAILED'; CANCELLED='CANCELLED'
TERMINAL={State.COMPLETED,State.FAILED,State.CANCELLED}
TRANSITIONS={State.PENDING:{State.FAILED,State.PLANNING,State.RUNNING,State.CANCELLED},State.PLANNING:{State.RUNNING,State.FAILED,State.CANCELLED,State.WAITING},State.RUNNING:{State.WAITING,State.VERIFYING,State.FAILED,State.CANCELLED},State.WAITING:{State.PLANNING,State.RUNNING,State.CANCELLED,State.FAILED},State.VERIFYING:{State.WAITING,State.RUNNING,State.COMPLETED,State.FAILED,State.CANCELLED}}
def transition(old: State,new: State):
    if new not in TRANSITIONS.get(old,set()): raise ServiceError('invalid_state_transition')
class Budget(Strict):
    llm_calls: int=Field(default=12,ge=1,le=30)
    tool_calls: int=Field(default=20,ge=1,le=50)
    seconds: int=Field(default=180,ge=5,le=600)
    concurrency: int=Field(default=2,ge=1,le=3)
class GoalInput(Strict):
    project_id: str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    goal: str=Field(min_length=1,max_length=2000)
    document_ids: list[str]=Field(default_factory=list,max_length=10)
    acceptance: list[str]=Field(default_factory=lambda:['Evidence references and exact quotes are valid.'],min_length=1,max_length=10)
    budget: Budget=Field(default_factory=Budget)
class Agent(Strict):
    id: str
    role: str
    capabilities: list[str]
    tools: list[str]
    timeout: int=90
    retries: int=1
    input_schema: str='Task'
    output_schema: str='TaskOutput'
AGENTS={a.id:a for a in [
 Agent(id='planning',role='Create validated task graph',capabilities=['planning'],tools=[]),
 Agent(id='research',role='Retrieve cited evidence',capabilities=['research'],tools=['rag_search','document_read']),
 Agent(id='execution',role='Execute approved tools',capabilities=['execution'],tools=['calculator','document_read','file_read']),
 Agent(id='analysis',role='Analyze evidence and compare measurements',capabilities=['analysis'],tools=['calculator','nlp_analyze','rag_search']),
 Agent(id='verification',role='Independent deterministic verification',capabilities=['verification'],tools=[]),
 Agent(id='reporting',role='Assemble evidence and limitations',capabilities=['reporting'],tools=[])]}
class Task(Strict):
    id: str=Field(pattern=r'^[a-zA-Z0-9_-]{1,40}$')
    description: str=Field(min_length=1,max_length=1000)
    agent: Literal['research','execution','analysis','verification','reporting']
    dependencies: list[str]=Field(default_factory=list,max_length=12)
    tools: list[str]=Field(default_factory=list,max_length=5)
    acceptance: list[str]=Field(min_length=1,max_length=6)
    max_retries: int=Field(default=1,ge=0,le=2)
    max_steps: int=Field(default=3,ge=1,le=5)
    condition: Literal['always','evidence_available']='always'
    @model_validator(mode='after')
    def permissions(self):
        if not set(self.tools)<=set(AGENTS[self.agent].tools): raise ValueError('tool permission denied')
        return self

class Plan(Strict):
    tasks: list[Task]=Field(min_length=1,max_length=12)
    @model_validator(mode='after')
    def valid(self):
        ids={t.id for t in self.tasks}
        if len(ids)!=len(self.tasks): raise ValueError('duplicate task IDs')
        visited=set()
        for t in self.tasks:
            if not set(t.dependencies)<=ids or t.id in t.dependencies: raise ValueError('invalid dependencies')
            if not set(t.tools)<=set(AGENTS[t.agent].tools): raise ValueError('tool permission denied')
        while len(visited)<len(ids):
            ready={t.id for t in self.tasks if set(t.dependencies)<=visited}-visited
            if not ready: raise ValueError('cyclic graph')
            visited|=ready
        return self
class Evidence(Strict):
    chunk_id: str
    document_id: str
    quote: str=Field(min_length=1,max_length=1800)
class Comparison(Strict):
    measurement: float
    requirement: float
    operator: Literal['>=','<=','>','<','==']
    unit: str
    measurement_quote: str
    requirement_quote: str
    tool_call_id: str
class TaskOutput(Strict):
    summary: str=Field(max_length=3000)
    evidence: list[Evidence]=Field(default_factory=list,max_length=12)
    comparisons: list[Comparison]=Field(default_factory=list,max_length=5)
    limitations: list[str]=Field(default_factory=list,max_length=10)
class Action(Strict):
    kind: Literal['tool','finish']
    tool: str | None=None
    arguments: dict[str,Any]=Field(default_factory=dict)
    output: TaskOutput | None=None
class Verification(Strict):
    outcome: Literal['PASS','FAIL','INCONCLUSIVE']
    criteria: list[dict[str,str]]
    limitations: list[str]=Field(default_factory=list)
