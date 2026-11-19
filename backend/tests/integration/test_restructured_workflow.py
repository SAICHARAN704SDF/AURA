import asyncio
from aura.agents.contracts import GoalInput, Plan, Task, TaskOutput
from aura.database.connection import open_workflow_database
from aura.memory.manager import Memory
from aura.orchestration.workflow.engine import Engine
from aura.orchestration.graph.workflow import build_graph


def test_database_initialization_preserves_rows(tmp_path):
    path = tmp_path / 'workflows.sqlite'
    db = open_workflow_database(path)
    db.execute("INSERT INTO goals VALUES ('sentinel','p','{}')")
    db.commit(); db.close()
    db = open_workflow_database(path)
    assert db.execute('SELECT id FROM goals').fetchall() == [('sentinel',)]
    assert db.execute('PRAGMA quick_check').fetchone() == ('ok',)
    db.close()


def test_langgraph_resumes_without_repeating_completed_task(tmp_path):
    async def check():
        memory = Memory(tmp_path / 'state.sqlite')
        goal = GoalInput(project_id='p', goal='Summarize evidence')
        plan = Plan(tasks=[Task(id='a', description='First', agent='analysis', tools=[], acceptance=['evidence']),
                           Task(id='b', description='Second', agent='analysis', tools=[], dependencies=['a'], acceptance=['evidence'])])
        gid = memory.create_goal(goal)
        wid = memory.create(gid, 'p', plan.model_dump())
        w = memory.get(wid, 'p')
        w['tasks']['a'] = {'state':'COMPLETED', 'attempt':0, 'failures':[], 'output':TaskOutput(summary='existing').model_dump()}
        memory.save(w, state='RUNNING')
        engine = Engine(None, memory, None)
        called = []
        async def worker(w,g,t):
            called.append(t.id)
            return TaskOutput(summary='new')
        engine.worker = worker
        graph = build_graph(engine, w, goal)
        assert {'planning','task_wave','verification'} <= set(graph.get_graph().nodes)
        result = await engine.execute(wid, 'p')
        assert called == ['b']
        assert result['tasks']['a']['output']['summary'] == 'existing'
        assert result['state'] == 'FAILED'  # Empty evidence must never become success.
        assert any(e['type']=='verification' for e in memory.events(wid,'p'))
        memory.close()
    asyncio.run(check())
