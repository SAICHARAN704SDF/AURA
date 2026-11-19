"""
FILE: backend/src/aura/orchestration/graph/nodes.py
PURPOSE: Prepare plans, schedule ready tasks and finalize checked reports.
MAIN RESPONSIBILITY: Langgraph Execution Nodes.
INPUTS: Engine, mutable workflow and validated goal.
OUTPUTS: Graph completion state and persisted workflow updates.
IMPORTANT FUNCTIONS / CLASSES: prepare, wave, finalize.
CONNECTED MODULES: aura.observability.events, aura.core, aura.agents.contracts, aura.agents.verification.checks, aura.agents.verification.claims.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "The graph joins independent research tasks before analysis and preserves failure status."
"""
# PRESENTATION SECTION: LANGGRAPH EXECUTION NODES
from aura.observability.events import traced, emit, span
import asyncio
from aura.core import ServiceError
from aura.agents.contracts import Plan
from aura.agents.verification.checks import verify

@traced('planning')
async def prepare(engine,w,goal):
    if goal.use_project_memory and 'prior_episodes' not in w:
        from aura.memory.semantic import nearest, recent_episodes
        embedding=engine.dispatcher.rag.embedding
        rows=recent_episodes(engine.memory,goal,embedding.model)
        try:
            w['prior_episodes']=nearest(rows,(await embedding.embed([goal.goal]))[0]) if rows else []
            engine.memory.save(w,{'type':'episode_recall','count':len(w['prior_episodes'])})
        except ServiceError as exc:
            w['prior_episodes']=[]
            engine.memory.save(w,{'type':'episode_recall_unavailable','error':exc.code})
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
    """Purpose: Dependency scheduling.
    
    Inputs: Engine, workflow and goal.
    Process and rationale: Select tasks whose dependencies completed, respect concurrency and await a TaskGroup; detect scheduler deadlock.
    Returns: Dictionary with complete flag.
    """
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
    """Purpose: Final report verification.
    
    Inputs: Engine, workflow and goal.
    Process and rationale: Run deterministic checks and leaf-output claim review; preserve partial limitations and save completed/failed report state.
    Returns: Graph complete flag with report persisted in workflow memory.
    """
    engine.memory.save(w,{'type':'verifying'},state='VERIFYING')
    outputs=[e['output'] for e in w['tasks'].values() if e.get('output')]
    verification=verify(outputs,engine.observations(w),goal)
    reviews=[]
    if engine.gateway is not None and verification.outcome!='FAIL':
        from aura.agents.verification.claims import review
        depended={d for task in w['plan']['tasks'] for d in task['dependencies']}
        for task_id,entry in w['tasks'].items():
            if task_id in depended or not entry.get('output'):continue
            output=entry['output']
            async def generate(schema,prompt,system):
                return await engine.llm(w,goal,schema,prompt,system)
            result=await review(output['summary'],[e['quote'] for e in output.get('evidence',[])],generate)
            if result['outcome']!='PASS':
                supported=[row['claim'] for row in result['claims'] if row['outcome']=='supported']
                if supported:
                    output['summary']='\n\n'.join(supported)
                    output.setdefault('limitations',[]).append('Unsupported or uncertain draft sentences were omitted after claim review. This is a partial report.')
                    result['draft_outcome']=result['outcome']
                    result['outcome']='PASS'
                    result['filtered_output']=True
                    engine.memory.put(w,'working',task_id,output)
            reviews.append({'task_id':task_id,**result})
        if not reviews or any(r['outcome']!='PASS' for r in reviews):
            verification.outcome='INCONCLUSIVE' if verification.outcome!='FAIL' else 'FAIL'
        verification.criteria.append({'criterion':'claim_support_review','outcome':'PASS' if reviews and all(r['outcome']=='PASS' for r in reviews) else 'INCONCLUSIVE'})
        verification.limitations.append('Independent model claim review is fallible; it is not a correctness guarantee.')
    w['report']={'claim_reviews':reviews,'verification':verification.model_dump(),'results':outputs,'limitations':verification.limitations,'tokens':w['tokens'],'llm_calls':w['llm_calls'],'tool_calls':w['tool_calls']}
    for i,o in enumerate(outputs):engine.memory.put(w,'semantic',str(i),{'evidence':o.get('evidence',[]),'trust':'untrusted_source'})
    state='COMPLETED' if verification.outcome=='PASS' else 'FAILED'
    if goal.use_project_memory and state=='COMPLETED':
        from aura.memory.semantic import store_episode
        summary=' '.join(w['tasks'][r['task_id']]['output']['summary'] for r in reviews)
        embedding=engine.dispatcher.rag.embedding
        try:
            vec=(await embedding.embed([goal.goal]))[0]
            store_episode(engine.memory,w['id'],goal,summary,embedding.model,vec)
            engine.memory.save(w,{'type':'episode_indexed'})
        except ServiceError as exc:
            engine.memory.save(w,{'type':'episode_index_unavailable','error':exc.code})
    w['error']=None if state=='COMPLETED' else 'verification_'+verification.outcome.lower()
    engine.memory.save(w,{'type':'verification','outcome':verification.outcome},state=state)
    return {"complete": True}
