"""Bounded supervisor, specialized workers, durable task graph execution."""
import asyncio,json,time
from aura.observability.events import current_trace
from pydantic import ValidationError
from aura.core import ServiceError
from aura.contracts import Request
from aura.agents.contracts import GoalInput,Plan,State,TERMINAL,AGENTS,Action
from aura.agents.worker import run_worker
from aura.orchestration.graph.workflow import build_graph

class Engine:
    def __init__(self,gateway,memory,dispatcher):
        self.gateway=gateway;self.memory=memory;self.dispatcher=dispatcher;self.running={};self.cancelled=set()
    async def llm(self,w,goal,schema,prompt,system):
        if w['llm_calls']>=goal.budget.llm_calls:raise ServiceError('llm_budget_exhausted')
        provider,model=self.gateway.preferred_generation()
        w['llm_calls']+=1;self.memory.save(w,{'type':'llm_started','provider':provider,'model':model})
        if model not in self.gateway.available.get(provider,[]):await self.gateway.discover(provider)
        result=await self.gateway.generate(provider,model,Request(prompt=prompt,max_tokens=2048),verify=True,schema=schema,system=system,function_output=schema is Action)
        w['tokens']+=result.tokens;self.memory.save(w,{'type':'llm_completed','provider':provider,'model':model,'tokens':result.tokens})
        return schema.model_validate_json(result.text)
    async def plan(self,w,goal):
        prompt=json.dumps({'goal':goal.goal,'acceptance':goal.acceptance,'agents':{k:v.tools for k,v in AGENTS.items()},'document_ids':goal.document_ids})
        return await self.llm(w,goal,Plan,prompt,'Create a compact dependency graph, usually research then analysis. Use research with rag_search to gather exact evidence; analysis with calculator to compare stated numbers. Verification and reporting run independently after all tasks. Each task acceptance must be measurable. Prefer 2 tasks: research using only rag_search (max_steps 3), then analysis with no tools and a dependency on research. Every tool listed in a task is REQUIRED, not merely available. Include calculator only for an explicit numeric comparison request. Do not add document_read unless necessary. Use condition=always for research and all root tasks. Use condition=evidence_available only when a task has dependencies that supply evidence. Maximum 4 tasks. Return the required JSON schema. Do not invent evidence.')
    def observations(self,w):
        rows=self.memory.db.execute("SELECT body FROM memory WHERE workflow=? AND project=? AND layer='episodic'",(w['id'],w['project_id']))
        return [json.loads(r[0]) for r in rows if 'call_id' in json.loads(r[0])]
    async def worker(self,w,goal,task):
        return await run_worker(self,w,goal,task)
    async def task(self,w,goal,t):
        entry=w['tasks'].setdefault(t.id,{'state':'PENDING','attempt':0,'failures':[]})
        while entry['attempt']<=t.max_retries:
            entry['state']='RUNNING';self.memory.save(w,{'type':'task_started','task_id':t.id,'agent_id':t.agent,'attempt':entry['attempt']})
            try:
                out=await asyncio.wait_for(self.worker(w,goal,t),AGENTS[t.agent].timeout)
                entry.update(state='COMPLETED',output=out.model_dump())
                self.memory.put(w,'working',t.id,out.model_dump())
                self.memory.save(w,{'type':'task_completed','task_id':t.id,'agent_id':t.agent});return
            except asyncio.CancelledError:raise
            except (ServiceError,ValidationError,TimeoutError) as e:
                code=getattr(e,'code',type(e).__name__);entry['failures'].append(code);entry['attempt']+=1
                self.memory.save(w,{'type':'task_failed','task_id':t.id,'error':code})
                if code in ('http_429','rate_limited','http_402','llm_budget_exhausted','tool_budget_exhausted'):raise ServiceError(code)
        entry['state']='FAILED';raise ServiceError('task_retry_exhausted')
    async def execute(self,id,project):
        token=current_trace.set(id)
        try:
            return await self._execute(id,project)
        finally:
            current_trace.reset(token)

    async def _execute(self,id,project):
        if id in self.running:raise ServiceError('workflow_already_running')
        w=self.memory.get(id,project)
        if State(w['state']) in TERMINAL:return w
        self.running[id]=asyncio.current_task();start=time.monotonic()
        goal=GoalInput.model_validate(self.memory.goal(w['goal_id'],project))
        try:
            w.setdefault('started_at',time.time())
            self.memory.save(w)
            remaining=min(goal.budget.seconds-w['elapsed'],goal.budget.seconds-(time.time()-w['started_at']))
            if remaining<=0:raise ServiceError('duration_budget_exhausted')
            async with asyncio.timeout(remaining):
                if w['state'] not in ('PENDING','WAITING'):
                    self.memory.save(w,{'type':'recovered'},state='WAITING')
                graph=build_graph(self,w,goal)
                await graph.ainvoke({"complete":False}, config={"recursion_limit":32})
        except asyncio.CancelledError:
            self.memory.save(w,{'type':'cancelled'},state='CANCELLED')
        except Exception as e:
            code=getattr(e,'code',type(e).__name__)
            if isinstance(e,BaseExceptionGroup):code=getattr(e.exceptions[0],'code',type(e.exceptions[0]).__name__)
            w['error']=code;self.memory.save(w,{'type':'failed','error':code},state='FAILED')
        finally:
            w['elapsed']+=time.monotonic()-start;self.memory.save(w);self.running.pop(id,None);self.cancelled.discard(id)
        return self.memory.get(id,project)
    def cancel(self,id,project):
        w=self.memory.get(id,project)
        if State(w['state']) in TERMINAL:return w
        self.cancelled.add(id)
        if id in self.running:self.running[id].cancel()
        else:self.memory.save(w,{'type':'cancelled'},state='CANCELLED')
        return self.memory.get(id,project)
    async def shutdown(self):
        for task in list(self.running.values()):task.cancel()
        await asyncio.gather(*list(self.running.values()),return_exceptions=True)
