# ResearchOS · AURA research workspace

A local student project combining Generative AI, Agentic AI and NLP. Upload documents, ask cited questions, generate bounded research reports, inspect language features and watch recorded workflow events. AURA uses existing hosted models; it does not train a foundation model.

**Open the workspace at http://127.0.0.1:3000.** The Research desk answers questions with passages from a selected paper. Agent workflows generate reviewed reports with a live task graph. Language lab explores entities, relations, summaries and the trained NER comparison.

Start the backend using the Python steps below. In a second terminal, start the Next.js interface:

```sh
cd apps/web
npm ci
npm run build
npm start
```

For Docker, follow [single-machine deployment](docs/deployment.md). For measured results and the five-phase checklist, see [release evidence](ROADMAP.md).

## Structure

```text
AURA/
├── apps/web/                  Next.js research workspace
├── datasets/samples/          labeled experiments
├── frontend/                  original lightweight interface
│   ├── index.html
│   ├── app.js
│   ├── subjects.js
│   ├── styles.css
│   └── tests/                 JavaScript workflow tests
├── backend/
│   ├── main.py                server launcher
│   ├── src/aura/
│   │   ├── api/               application and HTTP dashboard
│   │   ├── core/              settings, errors, logging
│   │   ├── rag/               ingestion, chunking, embeddings, vectorstore,
│   │   │                      retrieval, generation, prompts, API
│   │   ├── nlp/               linguistics, semantic similarity, API
│   │   ├── llm/               providers, gateway and transport
│   │   ├── agents/            contracts, workers, tools, verification
│   │   ├── orchestration/     graph, workflow engine, API
│   │   ├── memory/            workflow state
│   │   ├── database/          SQLite initialization
│   │   └── observability/     execution events
│   ├── tests/                 unit, integration, evaluation
│   ├── scripts/               setup and opt-in live demos/checks
│   └── reports/               preserved test evidence and outputs
├── data/                      existing persistent storage (ignored)
├── .env                       local credentials (ignored)
├── pyproject.toml             authoritative dependencies and packaging
├── Makefile                   install, serve and test commands
└── README.md
```

## Install and run

Use Python 3.12. Run all commands from the repository root, not inside backend, so the single .env and existing data paths resolve correctly. Keep any existing environment and .env; do not overwrite them.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m spacy download en_core_web_sm
python backend/scripts/setup_ocr.py
python backend/scripts/init_db.py
python backend/main.py
```

Open http://127.0.0.1:8000. OCR setup is optional for native-text documents. The original interface is available on port 8000. The new workspace runs on port 3000. Use one server worker for local Qdrant. If port 8000 is already occupied, use the existing server; do not start another process against the same local vector data.

## One local environment file

All project credentials belong in the ignored root `.env`. There is intentionally no example credential file. For a fresh checkout, create `.env` manually and supply your own values. Never commit it. Existing settings also accept environment-variable overrides.

| Variable name | Purpose |
|---|---|
| GROQ_API_KEY | Default generation provider credential |
| CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID | Embeddings and reranking |
| AURA_LLM_PROVIDER | groq by default; agentrouter is optional |
| GROQ_MODEL | Default openai/gpt-oss-20b |
| AGENTROUTER_API_KEY, AGENTROUTER_MODEL | Optional OpenCode/AgentRouter configuration |
| GEMINI_API_KEY, HF_TOKEN | Optional explicit provider verification paths |
| DATA_DIR | Storage root, default data |
| QDRANT_URL | Optional remote vector server; local storage is the default |
| TIMEOUT, CONCURRENCY, MAX_RSS_MB | Bounded transport settings |
| TESSDATA_PREFIX | Optional OCR language-data directory override |

See `backend/src/aura/core/settings.py` for validation/defaults. Source publication does not publish the local .env.

## Use and verify

Upload a supported PDF, TXT, Markdown, CSV, PNG or JPEG (maximum 5 MiB), select the intended documents and choose an operation. Quick answers retrieve evidence before generation. Reports use bounded agent tasks. NLP and similarity are explicit modes. Download Markdown, text, JSON or event traces. Saved replay is visibly recorded and makes no new generation call.

```sh
python -m pytest -q
python -m compileall -q backend/src backend/scripts backend/tests backend/main.py
python -m pip check
node --check frontend/app.js
node --check frontend/subjects.js
node frontend/tests/test_workflow_canvas.cjs
node frontend/tests/test_subject_workflows.cjs
node frontend/tests/test_replay.cjs
```

Node also builds and serves the Next.js workspace. Tests use mocks/temporary storage. Live verification scripts may consume provider quota; their outputs do not establish remaining account credits.

## Limitations

The code defaults to a small Groq model; no automatic expensive fallback is enabled for the main generation path. Exact citations and model claim review do not guarantee correctness. OCR can misread handwriting. The new UI streams real events over SSE; the original dashboard polls every 700 ms; model text is buffered. Detailed events are a bounded memory buffer; SQLite persists workflow records. This is a local single-user, unauthenticated application. Cloudflare AI is separate from a tunnel, which AURA does not manage.

## Show the actual LangGraph

Run `python backend/scripts/show_graph.py` (or `make graph`) from the root using the Python environment where AURA is installed. For Mermaid diagram source, run `python backend/scripts/show_graph.py --format mermaid`. These inspect the compiled graph without executing nodes, contacting model providers or consuming generation credits. The diagram shows orchestration topology, not live task progress.

## Live terminal workflow

While the server runs, execute `python backend/scripts/watch_live.py` and upload or ask a question in the website. The standard-library monitor polls real backend events and works without importing AURA or LangGraph. Use `--history` for buffered events, `--trace ID` to filter a run, or `--url http://127.0.0.1:8010` for another server. Ctrl+C stops only the monitor. Monitoring makes no generation requests; website operations can consume provider quota.

## Model and storage choices

The current deployment uses Groq generation, Cloudflare BGE-M3 embeddings, Qdrant vectors and SQLite state. The restructuring keeps existing database files readable. Set `AURA_LLM_PROVIDER` to groq, agentrouter, ollama, nvidia or openai_compatible. The verified paper runs used Groq openai/gpt-oss-20b. Compatible endpoints use `COMPATIBLE_BASE_URL`, `COMPATIBLE_MODEL` and, where required, `COMPATIBLE_API_KEY`. A model must support the structured responses used by the selected workflow.

To run passage retrieval locally, install the nlp-bench extra, cache sentence-transformers/all-MiniLM-L6-v2 using the embedding benchmark, and set `EMBEDDING_PROVIDER=local_minilm`. This uses a separate 384-dimensional collection and library under data/local-minilm. Import papers into that library. Local hybrid ranking uses lexical and vector retrieval. Configure the process memory limit for the model footprint if combining local ML and hosted generation.

Optional structured event logs use `RESEARCHOS_JSON_LOGS=1`. For tracing, install the observability extra, set `RESEARCHOS_OTEL=1` and run Uvicorn under `opentelemetry-instrument` with your collector configured. Exported stage spans carry the request correlation ID. This application is intended for a single trusted user.
