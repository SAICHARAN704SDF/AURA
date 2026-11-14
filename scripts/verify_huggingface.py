"""Small explicit hosted inference checks; never provisions or purchases credits."""
import asyncio
import json
import time
from pathlib import Path
from aura.core import Settings, ServiceError, configure_logging
from aura.contracts import Request
from aura.llm.gateway import Gateway
from aura.llm.transport import Transport
from aura.llm.registry import MODELS

async def main():
    configure_logging()
    t=Transport(Settings())
    g=Gateway(t.settings,t)
    report={}
    try:
        models=await g.discover('huggingface')
        # Verify account access separately; output no account identity or token details.
        account=await t.request('GET','https://huggingface.co/api/whoami-v2',headers=g.headers('huggingface'))
        if account.get('isPro') is not False:
            print('Stopped: free personal account status not established.')
            return
        for m in MODELS:
            if m.provider!='huggingface': continue
            if m.id not in models:
                report[m.id]={'success':False,'error':'not_hosted'}; continue
            start=time.monotonic()
            try:
                r=await g.generate('huggingface',m.id,Request(prompt='Reply only OK. /no_think',max_tokens=64),verify=True)
                report[m.id]={'success':True,'tokens':r.tokens,'seconds':round(time.monotonic()-start,3)}
            except ServiceError as e:
                report[m.id]={'success':False,'error':e.code}
                if e.code=='http_402':
                    report['remaining_checks']='Skipped: account credits exhausted; changing models does not replenish credit.'
                    break
        Path('reports/huggingface_verification.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
    finally: await t.close()
if __name__=='__main__': asyncio.run(main())
