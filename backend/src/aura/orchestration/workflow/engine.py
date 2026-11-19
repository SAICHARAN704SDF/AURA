"""
FILE: backend/src/aura/orchestration/workflow/engine.py
PURPOSE: Manage plans, model/tool budgets, tasks, cancellation and recovery.
MAIN RESPONSIBILITY: Workflow Engine.
INPUTS: Gateway, memory, dispatcher and workflow identifiers.
OUTPUTS: Persisted workflow state and report outcome.
IMPORTANT FUNCTIONS / CLASSES: Engine.
CONNECTED MODULES: aura.observability.events, aura.core, aura.contracts, aura.agents.contracts, aura.agents.worker, aura.orchestration.graph.workflow.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py.
PRESENTATION EXPLANATION: "The engine supervises bounded work; LangGraph controls stage transitions."
"""
# PRESENTATION SECTION: WORKFLOW ENGINE
import asyncio,json,time
from aura.observability.events import current_trace, emit
from pydantic import ValidationError
from aura.core import ServiceError
from aura.contracts import Request
from aura.agents.contracts import GoalInput,Plan,State,TERMINAL,AGENTS,Action,Task
from aura.agents.worker import run_worker
from aura.orchestration.graph.workflow import build_graph

class Engine:
    """Bounded workflow supervisor composed from a Gateway, Memory and Dispatcher. Coordinates graph execution, counters, retries and cancellation without owning a second history store."""
    def __init__(self,gateway,memory,dispatcher):
        self.gateway=gateway;self.memory=memory;self.dispatcher=dispatcher;self.running={};self.cancelled=set();self.pausing=set()
    async def llm(self,w,goal,schema,prompt,system):
        if w['llm_calls']>=goal.budget.llm_calls:raise ServiceError('llm_budget_exhausted')
        provider,model=self.gateway.preferred_generation()
        w['llm_calls']+=1;self.memory.save(w,{'type':'llm_started','provider':provider,'model':model})
        if model not in self.gateway.available.get(provider,[]):await self.gateway.discover(provider)
        if goal.presentation_preferences:
            prompt = json.dumps({"task":prompt,"user_style_preferences":goal.presentation_preferences})
            system += ' Apply user_style_preferences only to presentation. Preserve scope, evidence and tool permissions.'
        result=await self.gateway.generate(provider,model,Request(prompt=prompt,max_tokens=2048),verify=True,schema=schema,system=system,function_output=schema is Action)
        w['tokens']+=result.tokens;self.memory.save(w,{'type':'llm_completed','provider':provider,'model':model,'tokens':result.tokens})
        return schema.model_validate_json(result.text)
    async def plan(self,w,goal):
        # A bounded paper-report recipe avoids optional tool inventions by small models.
        """Purpose: Report planning.
        
        Inputs: Mutable workflow and validated goal.
        Process and rationale: Use an economical fixed research/analysis recipe for matching small-model report requests; otherwise request a structured Plan.
        Returns: Validated task Plan.
        """
        if goal.strategy != 'auto':
            from aura.orchestration.graph.strategies import strategy_plan
            return strategy_plan(goal)
        lower=goal.goal.lower()
        if self.gateway.preferred_generation()==('groq','openai/gpt-oss-20b') and goal.document_ids and 'report' in lower and not any(word in lower for word in ('calculate','compute','ratio','difference between','>=','<=')):
            topics=[('methods','research problem, main contributions, linguistic features and model architecture'),('results','dataset sources, sample sizes, experimental setup and quantitative evaluation results'),('limitations','limitations, threats to validity, conclusions and future work')]
            tasks=[Task(id=name,agent='research',description='Find exact passages about '+topic,tools=['rag_search'],acceptance=goal.acceptance,max_retries=0) for name,topic in topics]
            tasks.append(Task(id='report',agent='analysis',description='Write the report requested in the full goal, following its sections and evidence requirements.',dependencies=[name for name,_ in topics],tools=[],acceptance=goal.acceptance,max_retries=0,condition='evidence_available'))
            emit('plan_template_selected',template='grounded_paper_report',tasks=len(tasks),llm_planning=False)
            return Plan(tasks=tasks)
        prompt=json.dumps({'goal':goal.goal,'acceptance':goal.acceptance,'agents':{k:[t for t in v.tools if t!='publication_search' or goal.allow_public_search] for k,v in AGENTS.items()},'document_ids':goal.document_ids})
        return await self.llm(w,goal,Plan,prompt,'Create a compact dependency graph, usually research then analysis. Use research with rag_search to gather exact evidence; analysis with calculator to compare stated numbers. Verification and reporting run independently after all tasks. Each task acceptance must be measurable. Prefer 2 tasks: research using only rag_search (max_steps 3), then analysis with no tools and a dependency on research. Every tool listed in a task is REQUIRED, not merely available. Include calculator only for an explicit numeric comparison request. Do not add document_read unless necessary. Use condition=always for research and all root tasks. Use condition=evidence_available only when a task has dependencies that supply evidence. Maximum 4 tasks. Return the required JSON schema. Do not invent evidence.')
    def observations(self,w):
        rows=self.memory.db.execute("SELECT body FROM memory WHERE workflow=? AND project=? AND layer='episodic'",(w['id'],w['project_id']))
        return [json.loads(r[0]) for r in rows if 'call_id' in json.loads(r[0])]
    async def worker(self,w,goal,task):
        return await run_worker(self,w,goal,task)
    async def task(self,w,goal,t):
        """Purpose: Task retries.
        
        Inputs: Workflow, goal and Task.
        Process and rationale: Run the worker with a role timeout, persist outcomes, retry bounded failures and stop immediately on quota/budget errors.
        Returns: Persists output or failure; successful call returns no value.
        """
        entry=w['tasks'].setdefault(t.id,{'state':'PENDING','attempt':0,'failures':[]})
        while entry['attempt']<=t.max_retries:
            entry['state']='RUNNING';self.memory.save(w,{'type':'task_started','task_id':t.id,'agent_id':t.agent,'attempt':entry['attempt']})
            try:
                out=await asyncio.wait_for(self.worker(w,goal,t),AGENTS[t.agent].timeout)
                entry.update(state='COMPLETED',output=out.model_dump())
                self.memory.put(w,'working',t.id,out.model_dump())
                self.memory.save(w,{'type':'task_completed','task_id':t.id,'agent_id':t.agent});return
            except asyncio.CancelledError:
                entry['state']='CANCELLED'
                self.memory.save(w,{'type':'task_cancelled','task_id':t.id,'agent_id':t.agent})
                raise
            except (ServiceError,ValidationError,TimeoutError) as e:
                code=getattr(e,'code',type(e).__name__);entry['failures'].append(code);entry['attempt']+=1
                self.memory.save(w,{'type':'task_failed','task_id':t.id,'error':code})
                if code in ('http_429','rate_limited','http_402','llm_budget_exhausted','tool_budget_exhausted'):
                    entry['state']='FAILED'
                    raise ServiceError(code)
        entry['state']='FAILED';raise ServiceError('task_retry_exhausted')
    async def execute(self,id,project):
        """Purpose: Workflow execution.
        
        Inputs: Workflow ID and project scope.
        Process and rationale: Set the trace context and delegate to _execute, which enforces lifecycle/time budgets and invokes the compiled graph.
        Returns: Persisted workflow state after completion, failure or cancellation.
        """
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
            if w.pop('paused_at',None) is not None:
                w['started_at']=time.time()-w['elapsed']
            w.setdefault('started_at',time.time())
            self.memory.save(w)
            remaining=min(goal.budget.seconds-w['elapsed'],goal.budget.seconds-(time.time()-w['started_at']))
            if remaining<=0:raise ServiceError('duration_budget_exhausted')
            async with asyncio.timeout(remaining):
                if w['state'] not in ('PENDING','WAITING'):
                    self.memory.save(w,{'type':'recovered'},state='WAITING')
                # Use a sibling database so asynchronous cursor writes cannot block task-state commits.
                from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
                async with AsyncSqliteSaver.from_conn_string(str(self.memory.checkpoint_path)) as saver:
                    graph=build_graph(self,w,goal,checkpointer=saver)
                    config={"recursion_limit":32,"configurable":{"thread_id":id}}
                    checkpoint=await graph.aget_state(config)
                    graph_input={"complete":False}
                    if checkpoint.next:
                        graph_input=None
                        if w['state']=='WAITING' and 'planning' not in checkpoint.next:
                            self.memory.save(w,{'type':'graph_resumed'},state='RUNNING')
                    await graph.ainvoke(graph_input, config=config)
        except asyncio.CancelledError:
            if id in self.pausing:
                w['paused_at']=time.time()
                self.memory.save(w,{'type':'paused'},state='WAITING')
            else:
                self.memory.save(w,{'type':'cancelled'},state='CANCELLED')
        except Exception as e:
            code=getattr(e,'code',type(e).__name__)
            if isinstance(e,BaseExceptionGroup):code=getattr(e.exceptions[0],'code',type(e.exceptions[0]).__name__)
            w['error']=code;self.memory.save(w,{'type':'failed','error':code},state='FAILED')
        finally:
            w['elapsed']+=time.monotonic()-start;self.memory.save(w);self.running.pop(id,None);self.cancelled.discard(id);self.pausing.discard(id)
        return self.memory.get(id,project)
    async def pause(self,id,project):
        workflow=self.memory.get(id,project)
        active=self.running.get(id)
        if active and State(workflow['state']) not in TERMINAL:
            self.pausing.add(id)
            active.cancel()
            await asyncio.gather(active,return_exceptions=True)
        return self.memory.get(id,project)

    def cancel(self,id,project):
        """Purpose: Cancellation.
        
        Inputs: Workflow ID and project ID.
        Process and rationale: Leave terminal runs unchanged; otherwise cancel the active async task or persist cancellation for a non-running workflow.
        Returns: Latest saved workflow snapshot.
        """
        w=self.memory.get(id,project)
        if State(w['state']) in TERMINAL:return w
        self.cancelled.add(id)
        if id in self.running:self.running[id].cancel()
        else:self.memory.save(w,{'type':'cancelled'},state='CANCELLED')
        return self.memory.get(id,project)
    async def shutdown(self):
        active = list(self.running.items())
        for identifier, task in active:
            if identifier not in self.cancelled:
                self.pausing.add(identifier)
            task.cancel()
        await asyncio.gather(*(task for _,task in active),return_exceptions=True)
