"""Planning, bounded task waves, and independent verification nodes."""
from aura.observability.events import traced, emit, span
import asyncio
from aura.core import ServiceError
from aura.agents.contracts import Plan
from aura.agents.verification.checks import verify

@traced('planning')
async def prepare(engine,w,goal):
    if not w['plan']:
        engine.memory.save(w,{'type':'planning'},state='PLANNING')
        plan=await engine.plan(w,goal);w['plan']=plan.model_dump();engine.memory.save(w,{'type':'plan_validated'})
    else:
        engine.memory.save(w,{'type':'plan_loaded','tasks':len(w['plan']['tasks'])},state='PLANNING')
        plan=Plan.model_validate(w['plan'])
    engine.memory.save(w,{'type':'running'},state='RUNNING')
    return {"complete": False}

@traced('task_wave')
async def wave(engine,w,goal):
    plan=Plan.model_validate(w['plan'])
    done={id for id,e in w['tasks'].items() if e['state']=='COMPLETED'}
    if len(done)==len(plan.tasks):
        return {"complete": True}
    ready=[t for t in plan.tasks if t.id not in done and set(t.dependencies)<=done][:goal.budget.concurrency]
    if not ready:
        raise ServiceError('scheduler_deadlock')
    async with asyncio.TaskGroup() as group:
        for t in ready:
            group.create_task(engine.task(w,goal,t))
    done={id for id,e in w['tasks'].items() if e['state']=='COMPLETED'}
    return {"complete": len(done)==len(plan.tasks)}

@traced('verification')
async def finalize(engine,w,goal):
    engine.memory.save(w,{'type':'verifying'},state='VERIFYING')
    outputs=[e['output'] for e in w['tasks'].values() if e.get('output')]
    verification=verify(outputs,engine.observations(w),goal)
    w['report']={'verification':verification.model_dump(),'results':outputs,'limitations':verification.limitations,'tokens':w['tokens'],'llm_calls':w['llm_calls'],'tool_calls':w['tool_calls']}
    for i,o in enumerate(outputs):engine.memory.put(w,'semantic',str(i),{'evidence':o.get('evidence',[]),'trust':'untrusted_source'})
    state='COMPLETED' if verification.outcome=='PASS' else 'FAILED'
    w['error']=None if state=='COMPLETED' else 'verification_'+verification.outcome.lower()
    engine.memory.save(w,{'type':'verification','outcome':verification.outcome},state=state)
    return {"complete": True}
