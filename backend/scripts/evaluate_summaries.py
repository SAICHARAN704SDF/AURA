"""Measure extractive and optionally paid abstractive summaries through the app's NLP router.

Use --live only to authorize one configured provider call per evaluated reference.
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aura.core import ServiceError, Settings
from aura.llm.gateway import Gateway
from aura.llm.transport import Transport
from aura.nlp.api.routes import router
from aura.nlp.service import NLP
from evaluate_nlp import rouge


def evaluate(args):
    from contextlib import asynccontextmanager
    settings = Settings()
    @asynccontextmanager
    async def lifespan(app):
        app.state.nlp = NLP(None,settings.nlp_model,settings.nlp_domain_terms)
        transport = Transport(settings)
        gateway = app.state.gateway = Gateway(settings,transport)
        if args.live:
            await gateway.discover(gateway.preferred_generation()[0])
        try:
            yield
        finally:
            await transport.close()
    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    rows = [json.loads(line) for line in args.dataset.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r["split"]=="test" and r.get("summary")][:args.limit]
    if not rows:
        raise ValueError("No labeled test summaries found.")
    report = {"references":len(rows),"dataset":args.dataset.name,"modes":{}}
    with TestClient(app) as client:
        for mode in (["extractive","abstractive"] if args.live else ["extractive"]):
            records=[]
            for row in rows:
                try:
                    response = client.post("/nlp/summarize",json={"text":row["text"],"sentences":1,"mode":mode})
                    response.raise_for_status()
                    result=response.json()
                    records.append({"source":row["text"],"reference":row["summary"],"summary":result["text"],
                                    "metrics":rouge(result["text"],row["summary"]),"reported_tokens":result.get("tokens",0),
                                    "model":result.get("model",result["method"])})
                except ServiceError as exc:
                    records.append({"error":exc.code})
            ok=[r for r in records if "metrics" in r]
            report["modes"][mode]={"completed":len(ok),"failed":len(records)-len(ok),
                                  "mean_rouge_on_completed":{k:mean(r["metrics"][k] for r in ok) for k in ok[0]["metrics"]} if ok else None,
                                  "records":records}
    return report


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",type=Path,default=Path("datasets/samples/nlp_research.jsonl"))
    parser.add_argument("--limit",type=int,default=4)
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if args.limit<1:
        parser.error("limit must be positive")
    print(json.dumps(evaluate(args),indent=2))
