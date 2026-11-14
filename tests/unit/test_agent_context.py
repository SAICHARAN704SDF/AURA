import asyncio
import json
from types import SimpleNamespace
import pytest
from aura.agents.context import build_context
from aura.agents.contracts import GoalInput,Task,Action,TaskOutput
from aura.agents.worker import run_worker
from aura.agents.tools.dispatcher import ToolResult
from aura.core import ServiceError


def test_context_deduplicates_without_mutating_audit():
    goal=GoalInput(project_id='test',goal='Summarize')
    task=Task(id='research',description='Read',agent='research',tools=['rag_search'],acceptance=['evidence'])
    chunk={'id':'c','document_id':'d','text':'Exact evidence. '*200}
    observations=[{'call_id':str(i),'tool':'rag_search','data':{'chunks':[chunk]}} for i in range(5)]
    prompt=build_context(goal,task,[],observations,[],[], '')
    assert len(prompt)<=11000
    parsed=json.loads(prompt)
    assert sum(len(o['data']['chunks']) for o in parsed['observations'])==1
    assert observations[0]['data']['chunks'][0]['text']==chunk['text']
    assert parsed['required_tools_remaining']==[]


def test_missing_tool_feedback_recovers_without_restart():
    async def check():
        actions=iter([Action(kind='finish',output=TaskOutput(summary='premature')),
                      Action(kind='tool',tool='rag_search',arguments={'question':'test'}),
                      Action(kind='finish',output=TaskOutput(summary='done'))])
        prompts=[]
        async def llm(w,g,schema,prompt,system):prompts.append(json.loads(prompt));return next(actions)
        async def call(*args):return ToolResult(call_id='c',tool='rag_search',data={'chunks':[]})
        engine=SimpleNamespace(cancelled=set(),llm=llm,dispatcher=SimpleNamespace(catalog=lambda:[],call=call))
        task=Task(id='t',description='Read',agent='research',tools=['rag_search'],acceptance=['evidence'])
        result=await run_worker(engine,{'id':'w','tasks':{'t':{'failures':[],'attempt':0}}},GoalInput(project_id='p',goal='Read'),task)
        assert result.summary=='done'
        assert 'Do not finish' in prompts[1]['feedback']
        assert prompts[2]['required_tools_remaining']==[]
    asyncio.run(check())


def test_invented_inherited_citation_is_rejected():
    async def check():
        async def llm(*args):return Action(kind='finish',output=TaskOutput(summary='bad',evidence=[{'chunk_id':'c','document_id':'d','quote':'invented'}]))
        engine=SimpleNamespace(cancelled=set(),llm=llm,dispatcher=SimpleNamespace(catalog=lambda:[]))
        task=Task(id='t',description='Analyze',agent='analysis',tools=[],dependencies=['a'],acceptance=['evidence'])
        w={'id':'w','tasks':{'t':{'failures':[]},'a':{'output':{'summary':'prior','evidence':[{'chunk_id':'c','document_id':'d','quote':'real'}]}}}}
        with pytest.raises(ServiceError,match='invalid_citation'):await run_worker(engine,w,GoalInput(project_id='p',goal='Read'),task)
    asyncio.run(check())
