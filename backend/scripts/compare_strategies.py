"""Compare real generation routes on one frozen corpus with temporary indexes."""
import argparse
import asyncio
import hashlib
import json
import re
import tempfile
import time
from pathlib import Path

from aura.agents.contracts import GoalInput
from aura.api import create_app
from aura.contracts import Request
from aura.core import ServiceError, Settings


async def run(args):
    source = args.dataset.read_bytes()
    dataset = json.loads(source)
    records = []
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Settings(data_dir=directory, qdrant_url=None))
        async with app.router.lifespan_context(app):
            rag, engine, gateway = app.state.rag, app.state.engine, app.state.gateway
            provider, model = gateway.preferred_generation()
            report = {"dataset_sha256": hashlib.sha256(source).hexdigest(), "provider": provider,
                      "model": model, "scores": "Gold regex match; human factuality review required.", "runs": records}
            doc = None
            try:
                doc = (await rag.ingest("benchmark.txt", dataset["document"].encode()))["document"].id
            except ServiceError as exc:
                report["ingestion_error"] = exc.code
            for case in dataset["cases"][:args.limit]:
                for strategy in ("plain_llm", "single_rag", "single_react", "collaborative"):
                    started = time.monotonic()
                    initial_tokens = gateway.usage.get(provider, 0)
                    row = {"case": case["id"], "strategy": strategy, "success": False}
                    try:
                        if strategy == "plain_llm":
                            answer = (await gateway.generate(provider, model, Request(prompt=case["question"], max_tokens=512),
                                      verify=True, system="Answer the question concisely. State if you lack the required information.")).text
                        elif not doc:
                            raise ServiceError("benchmark_ingestion_failed")
                        elif strategy == "single_rag":
                            result = await rag.query(case["question"], document_id=doc)
                            answer = result["answer"].answer
                            row["citations"] = len(result["answer"].citations)
                            row["claim_review"] = result.get("claim_review", {}).get("outcome")
                        else:
                            goal = GoalInput(goal=case["question"], project_id="benchmark", document_ids=[doc], strategy=strategy)
                            gid = engine.memory.create_goal(goal)
                            wid = engine.memory.create(gid, goal.project_id)
                            w = await engine.execute(wid, goal.project_id)
                            row.update(state=w["state"], tool_calls=w["tool_calls"], llm_calls=w["llm_calls"])
                            if w["state"] != "COMPLETED":
                                raise ServiceError(w["error"] or "incomplete_workflow")
                            final = w["tasks"]["write" if strategy == "collaborative" else "research_answer"]["output"]
                            answer = final["summary"]
                            row["citations"] = len(final["evidence"])
                        row.update(answer=answer, success=True, gold_match=bool(re.search(case["gold_regex"], answer, re.I)))
                    except ServiceError as exc:
                        row["error"] = exc.code
                    row.update(seconds=round(time.monotonic()-started, 3),
                               reported_tokens=gateway.usage.get(provider, 0)-initial_tokens)
                    records.append(row)
                    args.output.write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parents[1]/"tests/fixtures/research_benchmark.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, choices=range(1, 4), default=3)
    asyncio.run(run(parser.parse_args()))
