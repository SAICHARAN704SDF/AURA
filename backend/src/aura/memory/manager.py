"""
FILE: backend/src/aura/memory/manager.py
PURPOSE: Persist scoped goals, workflow checkpoints, events and memory layers.
MAIN RESPONSIBILITY: Workflow Memory.
INPUTS: Workflow/project identifiers and serializable values.
OUTPUTS: Durable SQLite records and recovered dictionaries.
IMPORTANT FUNCTIONS / CLASSES: Memory.
CONNECTED MODULES: aura.observability.events, aura.database.connection, aura.core, aura.agents.contracts.
WHERE THIS FILE IS USED: backend/src/aura/orchestration/workflow/persistence.py.
PRESENTATION EXPLANATION: "This is application-level persistence, not LangGraph native checkpointing."
"""
# PRESENTATION SECTION: WORKFLOW MEMORY
import json, time, uuid
from aura.observability.events import emit, traced
from aura.database.connection import open_workflow_database
from pathlib import Path
from aura.core import ServiceError
from aura.agents.contracts import State,transition,TERMINAL
class Memory:
    """Project/workflow-scoped SQLite state owner. Takes a database path and persists goals, task snapshots, events and memory used for application-level recovery."""
    def __init__(self,path: Path):
        self.checkpoint_path=path.with_name(path.name + ".graph.sqlite")
        self.db=open_workflow_database(path)
    def create_goal(self,goal):
        id=str(uuid.uuid4())
        with self.db:self.db.execute('INSERT INTO goals VALUES (?,?,?)',(id,goal.project_id,goal.model_dump_json()))
        return id
    def goal(self,id,project):
        r=self.db.execute('SELECT body FROM goals WHERE id=? AND project=?',(id,project)).fetchone()
        if not r:raise ServiceError('goal_not_found')
        return json.loads(r[0])
    def create(self,goal_id,project,plan=None):
        self.goal(goal_id,project);id=str(uuid.uuid4())
        body={'plan':plan,'tasks':{},'llm_calls':0,'tool_calls':0,'tokens':0,'elapsed':0,'report':None,'error':None}
        with self.db:self.db.execute('INSERT INTO workflows VALUES (?,?,?,?,?,?)',(id,project,goal_id,'PENDING',json.dumps(body),time.time()))
        return id
    def get(self,id,project):
        r=self.db.execute('SELECT goal,state,body FROM workflows WHERE id=? AND project=?',(id,project)).fetchone()
        if not r:raise ServiceError('workflow_not_found')
        return {'id':id,'project_id':project,'goal_id':r[0],'state':r[1],**json.loads(r[2])}
    @traced('workflow_checkpoint')
    def save(self,w,event=None,state=None):
        """Purpose: Workflow persistence.
        
        Inputs: Mutable workflow, optional event and optional new state.
        Process and rationale: Validate transition and atomically persist workflow body plus lifecycle event; emit sanitized telemetry.
        Returns: Mutates saved workflow and its state; no return value.
        """
        old=self.get(w['id'],w['project_id'])['state']
        new=state or w['state']
        if old!=new:transition(State(old),State(new))
        body={k:v for k,v in w.items() if k not in ('id','project_id','goal_id','state')}
        # DATABASE OPERATION: Snapshot and lifecycle event commit in one SQLite transaction.
        with self.db:
            self.db.execute('UPDATE workflows SET state=?,body=?,updated=? WHERE id=? AND project=?',(new,json.dumps(body),time.time(),w['id'],w['project_id']))
            if event:self.db.execute('INSERT INTO events(workflow,project,body) VALUES (?,?,?)',(w['id'],w['project_id'],json.dumps({'time':time.time(),'state':new,**event})))
        w['state']=new
        if event:
            emit('workflow_event', event_type=event['type'], workflow_id=w['id'], workflow_state=new, **{k:v for k,v in event.items() if k!='type'})
    def put(self,w,layer,key,value):
        """Purpose: Memory layers.
        
        Inputs: Workflow, layer, key and serializable value.
        Process and rationale: Bound item size and upsert a workflow/project-scoped value; supports working outputs, episodic tool results and semantic evidence.
        Returns: SQLite memory record; no return value.
        """
        body=json.dumps(value)
        if len(body)>64000:raise ServiceError('memory_item_limit')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO memory VALUES (?,?,?,?,?)',(w['id'],w['project_id'],layer,key,body))
    def recall(self,w,layer,key):
        r=self.db.execute('SELECT body FROM memory WHERE workflow=? AND project=? AND layer=? AND key=?',(w['id'],w['project_id'],layer,key)).fetchone()
        return json.loads(r[0]) if r else None
    def events(self,id,project,after=0):
        self.get(id,project)
        return [{'sequence':r[0],**json.loads(r[1])} for r in self.db.execute('SELECT seq,body FROM events WHERE workflow=? AND project=? AND seq>? ORDER BY seq LIMIT 1000',(id,project,after))]
    def delete(self,id,project):
        w=self.get(id,project)
        if State(w['state']) not in TERMINAL:raise ServiceError('workflow_active')
        if self.checkpoint_path.exists():
            from langgraph.checkpoint.sqlite import SqliteSaver
            with SqliteSaver.from_conn_string(str(self.checkpoint_path)) as saver:
                saver.delete_thread(id)
        with self.db:
            for table in ('memory','events','research_episodes'):self.db.execute(f'DELETE FROM {table} WHERE workflow=? AND project=?',(id,project))
            self.db.execute('DELETE FROM workflows WHERE id=? AND project=?',(id,project))
    def prune(self,days=30):
        for id,project in self.db.execute("SELECT id,project FROM workflows WHERE updated<? AND state IN ('COMPLETED','FAILED','CANCELLED')",(time.time()-days*86400,)).fetchall():self.delete(id,project)
    def close(self):self.db.close()
