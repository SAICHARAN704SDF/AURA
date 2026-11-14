# AURA document research assistant

Python 3.12 backend for document indexing, cited answers, NLP, and auditable agent workflows. LLM inference is hosted; no local model weights are loaded.

## Project layout

```text
AURA/
├── main.py, pyproject.toml, requirements.txt, Makefile
├── .env.example, .gitignore
├── src/aura/
│   ├── core/           settings, errors, logging
│   ├── api/            FastAPI application
│   ├── nlp/            linguistics, semantic similarity, API
│   ├── rag/            ingestion, chunking, embeddings, vectorstore,
│   │                   retrieval, generation, prompts, API
│   ├── llm/            gateway, registry, transport, providers
│   ├── agents/         workers, contracts, tools, verification
│   ├── orchestration/  LangGraph, workflow lifecycle, API
│   ├── memory/         scoped persistent workflow memory
│   └── database/       SQLite connection and initialization
├── tests/              unit, integration, evaluation
├── scripts/            initialization, demos, verification, event watcher
├── docs/               architecture and feature guides, historical archive
├── reports/            demo results and historical archive
└── data/               existing SQLite, papers, vectors (ignored)
```

Core technologies: FastAPI, Pydantic, spaCy, Qdrant, SQLite3, LangGraph, LangChain-core, and hosted model providers. See [architecture](docs/architecture.md) for execution and recovery details.

## Setup

For a new checkout, copy `.env.example` to `.env` and fill in your credentials. Preserve an existing `.env`; never overwrite it or commit credentials. Python 3.12 is required. Cloudflare is used for embeddings and reranking. Select Groq or AgentRouter for answer generation with `AURA_LLM_PROVIDER`.

```sh
python3 -m pip install -e '.[test]'
python3 -m pytest -q
PYTHONPATH=src python3 scripts/init_db.py
PYTHONPATH=src python3 -m uvicorn aura.api:app --host 127.0.0.1 --port 8000
```

`PYTHONPATH=src python3 scripts/verify_models.py` performs small live provider checks. It is opt-in; unit tests never call cloud services. HTTP logs and raw error bodies are suppressed. No credentials or prompts are recorded in the report.

The API exposes diagnostics, document upload and search, cited RAG answers, NLP, and agent workflows. Startup performs provider discovery only. `/health` reports `unverified` until that process has successfully exercised a model.

`init_db.py` creates missing workflow tables without resetting data. The API initializes missing RAG tables and the vector collection on startup. Run commands from the repository root so relative `.env` and `data/` paths resolve consistently. After installation, `python3 main.py` also starts the API.

Offline checks: `python3 -m pytest -q`, `python3 -m compileall -q src scripts tests main.py`, and `python3 -m pip check`. The evaluation directory contains evidence-fidelity checks, not a live model benchmark.

See [the folder guide](docs/architecture.md) for the source tree and data flow.

## Document intelligence

Document uploads, persistent Qdrant hybrid retrieval, Cloudflare reranking, cited answers, and spaCy NLP are available. See [RAG](docs/rag.md), [NLP](docs/nlp.md), and [deployment](docs/deployment.md). Local NLP needs `python3 -m spacy download en_core_web_sm`. Use one server worker for local Qdrant.

## Small-model classroom demo

The dashboard defaults to Quick answer and uses `AURA_LLM_PROVIDER=groq` with `GROQ_MODEL=openai/gpt-oss-20b`. Supply your own Groq credentials. The visual canvas shows recorded execution events; click cards for explanations and expand technical details when needed. **Show saved example · no credits** replays a completed run without new AI calls. See [the demo guide](docs/demo.md). There is no automatic switch to a large model.

## Optional AgentRouter paper demo

Install the tested OpenCode CLI with `npm install --global opencode-ai@1.19.5`. Set `AGENTROUTER_API_KEY` in the ignored `.env`, then set `AURA_LLM_PROVIDER=agentrouter` and `AGENTROUTER_MODEL=gpt-5.6-sol`. Keep the Cloudflare credentials for embeddings and reranking. The AgentRouter adapter invokes the officially supported `opencode` CLI in an isolated temporary directory. It never writes the key to a tracked file. The model request is verified by inference because AgentRouter rejects direct model-list calls from generic HTTP clients. OpenCode adds its own prompt overhead, so reported token usage and latency can be higher than a direct model API call.

The demo downloads and indexes these four papers from arXiv when they are not already present:

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511)

Run:

```sh
PYTHONPATH=src python3 -u scripts/demo_papers.py --mode all
```

The terminal prints the plan, each agent transition, LLM call, tool call, retry, and verification outcome live. It writes the cited answer to `reports/paper-query.json`, the full event trace to `reports/papers-workflow.json` and `reports/papers-workflow.log`, and the paper report to `reports/papers-report.md`. To tail a workflow in a second terminal, use `PYTHONPATH=src python3 -u scripts/watch_workflow.py WORKFLOW_ID`. Existing Groq routing remains available by setting `AURA_LLM_PROVIDER=groq`.

## Local research dashboard

Run `make serve`, then open **http://127.0.0.1:8000**. The frontend is plain HTML/CSS/JavaScript in `frontend/`, served by FastAPI; no Node installation or frontend build is needed.

1. Upload PDF/TXT/Markdown/CSV documents (5 MB each), choosing recursive or semantic chunking. Select up to ten indexed documents.
2. Choose **Agent research report** for a multi-document agent run, **Cited answer** for one selected document, **Language analysis**, or **Semantic similarity** for two texts.
3. Enter the prompt and start. The execution map, dependency cards, stage badges, and expandable timeline update from real server events every 700 ms.
4. Download Markdown, text, JSON, or the current event trace. Saved workflows can be selected by project; interrupted workflows can be resumed and active workflows cancelled.

The UI displays parsing, chunking, embedding cache counts, vector writes, dense search, BM25 fusion, reranking/fallback, context assembly, NLP annotations, LangGraph stages, tools, provider requests, errors, and reported tokens when those operations actually run. Unused stages stay idle. Model text is buffered until completion, while execution events are live. Cancellation is available for agent workflows; single-request RAG/NLP operations complete as ordinary requests.

Detailed telemetry is a bounded 5,000-event in-memory buffer per server process. Export it before restarting. Workflow lifecycle events, task outputs, and reports remain in SQLite. A saved workflow's timeline restores its durable lifecycle events; older detailed telemetry may be unavailable. No API keys, request bodies, prompts, or raw provider error bodies are logged by the monitor. This is a local single-user dashboard, using AURA's existing unauthenticated API.

Cloudflare AI connectivity is separate from Cloudflare Tunnel. AURA does not start or verify `cloudflared`, so the dashboard labels tunnel status **unverified**. Credits and monetary cost remain **unknown**; reported token counts are not an account balance. No tunnel is launched automatically.

## Submission and implementation guide

- [How agents, RAG, NLP and LangGraph actually work](docs/how-it-works.md)
- [Fresh-checkout setup and demonstration steps](docs/demo.md)
- [Final validation results](reports/final-validation/README.md)

GitHub Actions runs offline tests, Python compilation, JavaScript syntax and dependency checks. The spaCy English model is installed during CI. Credentials, uploaded documents, vector indexes and local databases are excluded from Git. A clean checkout starts with empty local storage; upload your authorized papers before using document modes.
