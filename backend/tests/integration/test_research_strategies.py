import asyncio
import json

import httpx
import pytest
from aura.agents.contracts import GoalInput
from aura.agents.tools.research import evaluate_program
from aura.contracts import Request
from aura.core import Settings, ServiceError
from aura.llm.gateway import Gateway
from aura.llm.transport import Transport
from aura.orchestration.graph.strategies import strategy_plan


def test_reviewed_plan_dependencies_and_single_agent():
    goal = GoalInput(goal="Compare the two papers", project_id="study", strategy="collaborative")
    tasks = strategy_plan(goal).tasks
    assert [t.agent for t in tasks] == ["research","research","critic","writer"]
    assert tasks[2].dependencies == ["find","challenge"]
    assert tasks[-1].dependencies == ["find","challenge","critique"]
    assert len(strategy_plan(goal.model_copy(update={"strategy":"single_react"})).tasks)==1


@pytest.mark.parametrize("program", ["print(2)", "1/0", "3**100", "while True: pass", "open('input')","True","1e309"])
def test_numeric_program_rejects_unlisted_operations(program):
    with pytest.raises(ServiceError):
        evaluate_program(program)


def test_numeric_program_runs_local_arithmetic():
    assert evaluate_program("before=46\nafter=52\n(after-before)/before")["result"] == 6/46


@pytest.mark.parametrize("name",["ollama","nvidia","openai_compatible"])
def test_configured_compatible_llm_contract(name):
    async def run():
        settings=Settings(_env_file=None, aura_llm_provider=name, compatible_model="lab-model",
                          compatible_base_url="https://lab.example/v1", compatible_api_key="test",
                          max_rss_mb=4096)
        def handler(request):
            assert request.headers["authorization"]=="Bearer test"
            if request.url.path=="/v1/models":
                return httpx.Response(200,json={"data":[{"id":"lab-model"}]})
            assert request.url.path=="/v1/chat/completions"
            assert json.loads(request.content)["max_tokens"]==40
            return httpx.Response(200,json={"choices":[{"message":{"content":"result"}}],"usage":{"total_tokens":12}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            gateway=Gateway(settings,Transport(settings,client))
            await gateway.discover(name)
            result=await gateway.generate(*gateway.preferred_generation(),Request(prompt="Test",max_tokens=40),verify=True)
            assert (result.text,result.tokens)==("result",12)
    asyncio.run(run())


def test_semantic_memory_scopes_and_ranks(tmp_path):
    from aura.memory.manager import Memory
    from aura.memory.semantic import nearest, recent_episodes, store_episode
    memory = Memory(tmp_path/"workflows.sqlite")
    goal = GoalInput(project_id="p", goal="How often?", document_ids=["doc"])
    try:
        store_episode(memory,"w1",goal,"Short intervals","m",[1,0])
        store_episode(memory,"w2",goal,"Other result","m",[0,1])
        assert [r["workflow"] for r in nearest(recent_episodes(memory,goal,"m"),[1,0])]==["w1"]
        for changes in [{"project_id":"other"},{"document_ids":[]},{"document_ids":["doc","other"]}]:
            assert recent_episodes(memory,goal.model_copy(update=changes),"m")==[]
    finally:
        memory.close()


def test_paused_graph_resumes_after_reopening_database(tmp_path):
    from aura.agents.contracts import Plan, Task, TaskOutput
    from aura.memory.manager import Memory
    from aura.orchestration.workflow.engine import Engine
    async def run():
        path = tmp_path/"workflows.sqlite"
        memory = Memory(path)
        engine = Engine(None,memory,None)
        goal = GoalInput(project_id="scope",goal="Research")
        plan = Plan(tasks=[Task(id="a",description="first",agent="analysis",acceptance=["quote"]),
                           Task(id="b",description="second",agent="analysis",dependencies=["a"],acceptance=["quote"])])
        wid = memory.create(memory.create_goal(goal),goal.project_id,plan.model_dump())
        started=asyncio.Event()
        calls=[]
        async def worker(w,g,t):
            calls.append(t.id)
            if t.id=="b":
                started.set()
                await asyncio.sleep(60)
            return TaskOutput(summary="test")
        engine.worker=worker
        running=asyncio.create_task(engine.execute(wid,goal.project_id))
        await asyncio.wait_for(started.wait(),5)
        assert (await engine.pause(wid,goal.project_id))["state"]=="WAITING"
        await running
        memory.close()
        memory=Memory(path)
        engine=Engine(None,memory,None)
        async def finish(w,g,t):
            calls.append(t.id)
            return TaskOutput(summary="test")
        engine.worker=finish
        completed=await engine.execute(wid,goal.project_id)
        assert completed["tasks"]["b"]["state"]=="COMPLETED"
        assert completed["state"]=="FAILED"  # fixture deliberately has no citations
        assert calls==["a","b","b"]
        assert memory.checkpoint_path.is_file()
        memory.close()
    asyncio.run(run())
