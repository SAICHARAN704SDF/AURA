"""Bounded live API demonstration. Run against the already running AURA server.
Writes an audit per feature; never deletes user documents or changes providers.
"""
import argparse,json,time,uuid
from pathlib import Path
import httpx

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pause',type=float,default=3);parser.add_argument('--start-delay',type=float,default=20);args=parser.parse_args()
    base='http://127.0.0.1:8000';trace='demo-'+uuid.uuid4().hex[:12];project='feature_demo';out=Path('backend/reports')/trace;out.mkdir(parents=True)
    client=httpx.Client(base_url=base,timeout=150,headers={'X-Aura-Trace':trace});results=[]
    docs=client.get('/documents').json();paper=next(d for d in docs if 'Synergizing' in d['filename']);paper_id=paper['id']
    goal=client.post('/goals',json={'project_id':project,'goal':'Write a report on the research problem, methods, datasets, results and limitations in this paper. Use exact evidence and state what the retrieved excerpts do not establish.','document_ids':[paper_id],'budget':{'llm_calls':4,'tool_calls':6,'seconds':180,'concurrency':1}});goal.raise_for_status()
    workflow=client.post('/workflows',json={'project_id':project,'goal_id':goal.json()['id']});workflow.raise_for_status();wid=workflow.json()['id'];params={'project_id':project}
    watch=f'{base}/?watch={wid}&trace={trace}&project={project}'
    manifest={'trace':trace,'workflow':wid,'project':project,'watch_url':watch,'paper':paper['filename'],'directory':str(out)}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2));Path('backend/reports/latest-feature-demo.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest),flush=True)
    time.sleep(args.start_delay)
    def step(name,method,path,expected=200,check=None,**kw):
        print('START '+name,flush=True);start=time.monotonic()
        try:
            response=client.request(method,path,**kw);data=response.json();ok=response.status_code==expected
            if ok and check:ok=bool(check(data))
            row={'feature':name,'pass':ok,'http_status':response.status_code,'seconds':round(time.monotonic()-start,2)}
            (out/(name+'.json')).write_text(json.dumps(data,indent=2))
        except Exception as exc:row={'feature':name,'pass':False,'error':type(exc).__name__};data=None
        results.append(row);(out/'checks.json').write_text(json.dumps(results,indent=2));print(json.dumps(row),flush=True);time.sleep(args.pause);return data
    detail=step('document_read','GET','/documents/'+paper_id,check=lambda d:len(d['pages'])>0)
    text='\n'.join(p['text'] for p in detail['pages'][:3])[:6500]
    recursive=step('upload_recursive','POST','/documents/upload',files={'file':('DEMO_recursive_excerpt.txt',('DEMO excerpt for indexing checks.\n'+text).encode())},check=lambda d:d.get('chunks',0)>0 or d.get('duplicate'))
    step('duplicate_upload','POST','/documents/upload',files={'file':('DEMO_recursive_excerpt.txt',('DEMO excerpt for indexing checks.\n'+text).encode())},check=lambda d:d.get('duplicate') is True)
    step('upload_semantic','POST','/documents/upload?strategy=semantic',files={'file':('DEMO_semantic_excerpt.txt',('DEMO excerpt for semantic chunking checks.\n'+text).encode())},check=lambda d:d.get('strategy')=='semantic' or d.get('duplicate'))
    step('nlp','POST','/nlp/analyze',json={'text':'Researchers use DistilBERT to study AI-generated text. Alice presented the results in London.'},check=lambda d:len(d['tokens'])>0 and len(d['sentences'])==2)
    pair={'first':'The model detects text written by artificial intelligence.','second':'The system identifies AI-generated writing.'}
    step('similarity','POST','/nlp/similarity',json=pair,check=lambda d:-1.0001<=d['cosine']<=1.0001)
    step('similarity_cached','POST','/nlp/similarity',json=pair,check=lambda d:-1.0001<=d['cosine']<=1.0001)
    step('retrieval','POST','/retrieval/search',json={'question':'What linguistic features and transformer models are used?','document_id':paper_id,'top_k':3},check=lambda d:bool(d['chunks']) and all(c['document_id']==paper_id for c in d['chunks']))
    step('cited_answer','POST','/rag/query',json={'question':'Which linguistic features are described? Give a concise answer with exact supporting quotes.','document_id':paper_id},check=lambda d:bool(d['answer']['citations']))
    step('invalid_file','POST','/documents/upload',expected=415,files={'file':('demo.exe',b'not a valid document')})
    step('invalid_input','POST','/nlp/analyze',expected=422,json={'text':''})
    for path in ['/health','/providers/status','/models','/rag/status','/nlp/status','/agents','/tools']:
        step('status_'+path.strip('/').replace('/','_'),'GET',path)
    step('agent_report_start','POST',f'/workflows/{wid}/execute',expected=202,params=params)
    deadline=time.monotonic()+190
    while time.monotonic()<deadline:
        state=client.get('/workflows/'+wid,params=params).json()
        if state['state'] in ('COMPLETED','FAILED','CANCELLED'):break
        time.sleep(2)
    step('agent_report','GET','/workflows/'+wid,params=params,check=lambda d:d['state']=='COMPLETED' and d['report']['verification']['outcome']=='PASS')
    step('saved_report','GET',f'/workflows/{wid}/report',params=params,check=lambda d:d['state']=='COMPLETED')
    step('saved_events','GET',f'/workflows/{wid}/events',params=params,check=lambda d:bool(d['events']))
    step('history','GET','/monitor/workflows',params=params,check=lambda d:any(r['id']==wid for r in d))
    events=client.get('/monitor/events').json()['events'];events=[e for e in events if e.get('trace_id') in (trace,wid) or e.get('workflow_id')==wid]
    (out/'trace.json').write_text(json.dumps(events,indent=2))
    print('DONE '+str(out),flush=True)
if __name__=='__main__':main()
