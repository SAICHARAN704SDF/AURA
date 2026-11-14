"""Explicit, small live checks. Never prints credentials or provider error bodies."""
import asyncio, json, time
from pathlib import Path
import psutil
from aura.core import Settings, ServiceError, configure_logging
from aura.llm.transport import Transport
from aura.llm.gateway import Gateway
from aura.contracts import Request

async def main():
    configure_logging()
    t=Transport(Settings()); g=Gateway(t.settings,t)
    report={'providers':{},'inference':{},'ocr':'endpoint_not_verified'}
    try:
        for p in g.keys:
            models=await g.discover(p)
            report['providers'][p]={'status':g.status[p].model_dump(),'models':models}
        choices={'groq':['openai/gpt-oss-120b','llama-3.3-70b-versatile'], 'gemini':['gemini-3.8-flash','gemini-3.5-flash-lite','gemini-2.5-flash','gemini-2.0-flash']}
        for p,options in choices.items():
            model=next((m for m in options if m in g.available.get(p,[])),None)
            if not model: report['inference'][p]={'error':'no_selected_model_available'}; continue
            start=time.monotonic()
            try:
                r=await g.generate(p,model,Request(prompt='Reply with the word OK.',max_tokens=128),verify=True)
                report['inference'][p]={'model':model,'success':True,'tokens':r.tokens,'seconds':round(time.monotonic()-start,3)}
            except ServiceError as e: report['inference'][p]={'model':model,'error':e.code}
        for task in ('embed','rerank'):
            try:
                r=await g.embed(['A small verification sentence.']) if task=='embed' else await g.rerank('cat',['A cat is an animal.','A stone is a mineral.'])
                report['inference'][task]={'success':True,'items':len(r)}
            except ServiceError as e: report['inference'][task]={'error':e.code}
        report['rss_mb']=round(psutil.Process().memory_info().rss/1024**2,2)
        Path('reports').mkdir(exist_ok=True)
        Path('reports/verification.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({'inference':report['inference'],'rss_mb':report['rss_mb']}))
    finally: await t.close()
if __name__=='__main__': asyncio.run(main())
