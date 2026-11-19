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


def test_small_model_search_executes_once_then_validates_output():
    async def check():
        calls=[]
        async def call(*args):
            calls.append(args)
            return ToolResult(call_id='c',tool='rag_search',data={'chunks':[{'id':'c','document_id':'d','text':'Exact observed evidence.'}]})
        async def llm(w,g,schema,prompt,system):
            assert schema is TaskOutput
            assert json.loads(prompt)['required_tools_remaining']==[]
            return TaskOutput(summary='Summary',evidence=[{'chunk_id':'c','document_id':'d','quote':'Exact observed evidence.'}])
        engine=SimpleNamespace(cancelled=set(),gateway=SimpleNamespace(preferred_generation=lambda:('groq','openai/gpt-oss-20b')),llm=llm,dispatcher=SimpleNamespace(call=call))
        task=Task(id='t',description='Explain methods',agent='research',tools=['rag_search'],acceptance=['evidence'])
        result=await run_worker(engine,{'id':'w','tasks':{'t':{'failures':[],'attempt':0}}},GoalInput(project_id='p',goal='Report',document_ids=['d']),task)
        assert result.evidence[0].chunk_id=='c'
        assert result.evidence[0].quote=='Exact observed evidence.'
        assert len(calls)==1
    asyncio.run(check())


def test_report_indices_materialize_verbatim_quotes_and_labels():
    from aura.agents.worker import EvidenceDraft, materialize_draft
    catalog=[{'chunk_id':str(i),'document_id':'d','quote':'Exact source '+str(i)} for i in range(4)]
    draft=EvidenceDraft(summary='Methods [3], results [1,3].',evidence_indices=[3,1],limitations=[])
    output=materialize_draft(draft,catalog)
    assert output.summary=='Methods [Source 1], results [Source 2, 1].'
    assert [e.quote for e in output.evidence]==['Exact source 3','Exact source 1']
    draft.evidence_indices=[9]
    with pytest.raises(ServiceError,match='invalid_citation'):materialize_draft(draft,catalog)


def test_standard_paper_report_uses_bounded_template():
    from aura.orchestration.workflow.engine import Engine
    async def check():
        engine=Engine(SimpleNamespace(preferred_generation=lambda:('groq','openai/gpt-oss-20b')),None,None)
        plan=await engine.plan({},GoalInput(project_id='demo',goal='Write a detailed report',document_ids=['paper']))
        assert len(plan.tasks)==4
        assert plan.tasks[-1].dependencies==['methods','results','limitations']
        assert plan.tasks[-1].tools==[]
        assert all(t.tools==['rag_search'] for t in plan.tasks[:3])
    asyncio.run(check())


def test_indexed_answer_materializes_exact_source():
    from aura.rag.generation.generator import IndexedAnswer,resolve_answer
    sources=[{'chunk_id':'c','text':'Verbatim\nsource.'}]
    answer=resolve_answer(IndexedAnswer(answer='Example',insufficient_evidence=False,source_indices=[0]),sources)
    assert answer.citations[0].quote=='Verbatim\nsource.'
    with pytest.raises(ServiceError,match='invalid_citation'):
        resolve_answer(IndexedAnswer(answer='Example',insufficient_evidence=False,source_indices=[4]),sources)


def test_multi_paper_synthesis_prompt_is_bounded_and_balanced():
    from aura.agents.worker import bounded_evidence_prompt
    from aura.contracts import Request
    catalog=[{'document_id':doc,'chunk_id':f'{doc}-{i}','quote':'Evidence "quoted" words. '*100}
             for doc in ('first','second') for i in range(6)]
    prompt,selected=bounded_evidence_prompt('Compare these papers','Write a report',catalog)
    Request(prompt=prompt)
    assert len(prompt)<=11500
    assert [e['document_id'] for e in selected[:2]]==['first','second']
    assert all(any(e['quote'] in original['quote'] for original in catalog) for e in selected)


def test_long_report_goal_preserved_without_overflowing_task_description():
    import asyncio
    from aura.agents.contracts import GoalInput
    from aura.orchestration.workflow.engine import Engine
    class Gateway:
        def preferred_generation(self):return ('groq','openai/gpt-oss-20b')
    goal=GoalInput(project_id='test',goal='Write a report. '+('Detailed requirements. '*60),document_ids=['paper'])
    plan=asyncio.run(Engine(Gateway(),None,None).plan({},goal))
    assert len(plan.tasks[-1].description)<=1000
    assert len(goal.goal)>1000
