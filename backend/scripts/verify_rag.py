"""Real cloud RAG acceptance test; isolated temporary persistent storage."""
import asyncio,json,tempfile,time
from pathlib import Path
import psutil
from aura.core import Settings,configure_logging
from aura.llm.transport import Transport
from aura.llm.gateway import Gateway
from aura.rag.pipeline import Pipeline
async def main():
 configure_logging();t=Transport(Settings());g=Gateway(t.settings,t)
 report={'rss_before_mb':psutil.Process().memory_info().rss/1024**2}
 try:
  with tempfile.TemporaryDirectory() as directory:
   p=Pipeline(g,Path(directory)); start=time.monotonic()
   try:
    result=await p.ingest('observatory.txt',b'The fictional Lumen Observatory opened in 2019. Its telescope mirror has a diameter of 2.4 meters. The observatory is located on Cedar Hill.')
    report['document_id']=result['document'].id
    answer=await p.query('What is the diameter of the telescope mirror at Lumen Observatory?')
    report['answer']=answer['answer'].model_dump();report['reranked']=answer['retrieval']['reranked'];report['usage']=answer['usage']
    assert answer['answer'].citations and '2.4' in answer['answer'].answer
    report['rss_after_ingest_mb']=psutil.Process().memory_info().rss/1024**2
    report['embedding_calls']=p.embedding.calls
   finally:p.close()
   p=Pipeline(g,Path(directory))
   try: report['persistence_passed']=bool((await p.search('mirror'))['chunks'])
   finally:p.close()
   report['seconds']=time.monotonic()-start
 except Exception as e: report['error']=getattr(e,'code',type(e).__name__)
 finally:await t.close()
 Path('backend/reports/phase2-live.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':asyncio.run(main())
