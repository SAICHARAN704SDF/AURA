import asyncio
import pytest
from pydantic import ValidationError
from aura.agents.contracts import GoalInput,Plan,Task,State,transition,TaskOutput
from aura.orchestration.workflow.persistence import Memory
from aura.agents.tools.dispatcher import Dispatcher
from aura.orchestration.workflow.engine import Engine
from aura.core import ServiceError

def task(id='one',deps=[]):return Task(id=id,description='Compare numbers',agent='execution',tools=['calculator'],dependencies=deps,acceptance=['comparison'])
def test_graph():
 with pytest.raises(ValidationError):Plan(tasks=[task(),task()])
 with pytest.raises(ValidationError):Plan(tasks=[task('a',['b']),task('b',['a'])])
 with pytest.raises(ValidationError):Task(id='a',description='x',agent='research',tools=['calculator'],acceptance=['x'])
 with pytest.raises(ServiceError):transition(State.COMPLETED,State.RUNNING)
def setup(tmp_path):
 m=Memory(tmp_path/'memory');g=GoalInput(project_id='p',goal='Compare numbers');id=m.create_goal(g);w=m.get(m.create(id,'p'),'p');return m,g,w
def test_memory(tmp_path):
 m,g,w=setup(tmp_path);m.put(w,'working','x',{'value':1});m.close();m=Memory(tmp_path/'memory')
 assert m.recall(w,'working','x')=={'value':1}
 with pytest.raises(ServiceError):m.get(w['id'],'other')
 m.close()
def test_tools(tmp_path):
 async def check():
  m,g,w=setup(tmp_path);d=Dispatcher(None,None,tmp_path,m)
  r=await d.call(w,task(),g,'calculator',{'left':2.4,'right':2,'operation':'>='},'call')
  assert r.data['result'] is True
  await d.call(w,task(),g,'calculator',{'left':2.4,'right':2,'operation':'>='},'call');assert w['tool_calls']==1
  with pytest.raises(ServiceError):await d.call(w,task(),g,'file_read',{'name':'a.txt'},'bad')
  with pytest.raises(ValidationError):await d.call(w,task(),g,'calculator',{'left':'x','right':2,'operation':'eval'},'bad')
  m.close()
 asyncio.run(check())
def test_scheduler_recovery_cancel(tmp_path):
 async def check():
  m,g,w=setup(tmp_path);w['plan']=Plan(tasks=[task('a'),task('b'),task('c',['a','b'])]).model_dump();m.save(w)
  e=Engine(None,m,None);active=0;peak=0
  async def worker(w,g,t):
   nonlocal active,peak
   active+=1;peak=max(peak,active);await asyncio.sleep(.01);active-=1
   return TaskOutput(summary='done')
  e.worker=worker
  r=await e.execute(w['id'],'p');assert peak==2;assert len(r['tasks'])==3;assert r['state']=='FAILED' # no fabricated evidence
  before=len(m.events(w['id'],'p'));await e.execute(w['id'],'p');assert len(m.events(w['id'],'p'))==before
  id=m.create(w['goal_id'],'p');e.cancel(id,'p');assert m.get(id,'p')['state']=='CANCELLED'
  m.close()
 asyncio.run(check())

def test_retry_budget_and_cancel(tmp_path):
 async def check():
  m,g,w=setup(tmp_path);w['plan']=Plan(tasks=[task()]).model_dump();m.save(w)
  e=Engine(None,m,None);calls=0
  async def fail(*args):
   nonlocal calls
   calls+=1;raise ServiceError('invalid_structured_output')
  e.worker=fail
  r=await e.execute(w['id'],'p');assert r['state']=='FAILED' and calls==2
  wid=m.create(w['goal_id'],'p',Plan(tasks=[task()]).model_dump())
  async def slow(*args):await asyncio.sleep(20)
  e.worker=slow
  job=asyncio.create_task(e.execute(wid,'p'));await asyncio.sleep(.01);e.cancel(wid,'p');await job
  assert m.get(wid,'p')['state']=='CANCELLED'
  assert m.get(wid,'p')['tasks']['one']['state']=='CANCELLED';m.close()
 asyncio.run(check())

def test_restart_incomplete(tmp_path):
 async def check():
  m,g,w=setup(tmp_path);w['plan']=Plan(tasks=[task()]).model_dump();m.save(w,state='RUNNING');m.close()
  m=Memory(tmp_path/'memory');e=Engine(None,m,None)
  async def done(*args):return TaskOutput(summary='done')
  e.worker=done;r=await e.execute(w['id'],'p')
  assert r['tasks']['one']['state']=='COMPLETED'
  assert any(x['type']=='recovered' for x in m.events(w['id'],'p'));m.close()
 asyncio.run(check())

def test_agent_api(tmp_path):
 from fastapi.testclient import TestClient
 from aura.api import create_app
 from aura.core import Settings
 with TestClient(create_app(Settings(_env_file=None,data_dir=str(tmp_path)))) as c:
  r=c.post('/goals',json={'project_id':'p','goal':'test'});assert r.status_code==200
  gid=r.json()['id'];wid=c.post('/workflows',json={'project_id':'p','goal_id':gid}).json()['id']
  assert c.get('/workflows/'+wid+'?project_id=other').status_code==404
  assert c.post('/workflows/'+wid+'/cancel?project_id=p').json()['state']=='CANCELLED'
  assert c.get('/agents').status_code==200
  assert c.get('/tools').status_code==200
