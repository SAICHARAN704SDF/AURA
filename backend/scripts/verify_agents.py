"""Real goal planning, evidence retrieval, calculation and verification."""
import asyncio,json,tempfile,time
from pathlib import Path
import psutil
from aura.core import Settings,configure_logging
from aura.llm.transport import Transport
from aura.llm.gateway import Gateway
from aura.rag.pipeline import Pipeline
from aura.nlp.service import NLP
from aura.agents.contracts import GoalInput
from aura.orchestration.workflow.persistence import Memory
from aura.agents.tools.dispatcher import Dispatcher
from aura.orchestration.workflow.engine import Engine
async def main():
 configure_logging();t=Transport(Settings());g=Gateway(t.settings,t)
 with tempfile.TemporaryDirectory() as directory:
  path=Path(directory);p=Pipeline(g,path);m=Memory(path/'workflows.sqlite')
  try:
   d=(await p.ingest('known.txt',b'The Lumen telescope mirror diameter is 2.4 meters. The stated minimum mirror diameter requirement is 2.0 meters.'))['document']
   goal=GoalInput(project_id='acceptance',goal='Identify the reported mirror diameter, compare it with the stated minimum requirement using calculator, and report the comparison with exact citations.',document_ids=[d.id],acceptance=['Compare the reported measurement with the stated requirement.','Evidence references and exact quotes are valid.'])
   id=m.create_goal(goal);wid=m.create(id,goal.project_id)
   engine=Engine(g,m,Dispatcher(p,NLP(p.embedding),path/'files',m))
   result=await engine.execute(wid,goal.project_id)
   report={'workflow':result,'events':m.events(wid,goal.project_id),'rss_mb':psutil.Process().memory_info().rss/1024**2,'embedding_calls':p.embedding.calls}
   Path('backend/reports/phase3-live.json').write_text(json.dumps(report,indent=2))
   print(json.dumps({'state':result['state'],'error':result['error'],'tokens':result['tokens'],'llm_calls':result['llm_calls'],'tool_calls':result['tool_calls'],'rss_mb':report['rss_mb']}))
  finally:m.close();p.close();await t.close()
if __name__=='__main__':asyncio.run(main())
