# AURA restructuring report — 2026-11-10

## Audit and preservation

Baseline: 35 tests passed, with five existing PyMuPDF SWIG deprecation warnings. Git has no commits; source was untracked. The existing source was copied outside the repository before edits; no Git reset or commit was performed. Static imports, package layout, scripts, runtime asset paths, environment configuration names, provider protocols, documentation, tests, and SQLite schemas were inspected. Historical reports and planning documents contain unique context and were preserved. No unused implementation was sufficiently proven to justify deleting source functionality.

The baseline used a custom asyncio workflow scheduler and did not import LangGraph or LangChain. Existing AgentRouter integration uses OpenCode, not generic direct HTTP. No frontend or frontend build exists. The existing NLP implements linguistic analysis and semantic similarity, not intent classification, language detection, or OCR.

## Final folder tree

Actual tree after cleanup (Git internals omitted; secret file contents are never included):

```text
AURA/
├── .vscode/
│   └── settings.json
├── data/
│   ├── papers/
│   │   ├── attention-is-all-you-need.pdf
│   │   ├── react.pdf
│   │   ├── retrieval-augmented-generation.pdf
│   │   └── self-rag.pdf
│   ├── vectors/
│   │   ├── collection/
│   │   │   └── aura_bge_m3_1024_v1/
│   │   │       └── storage.sqlite
│   │   ├── .lock
│   │   └── meta.json
│   ├── embeddings.sqlite
│   ├── workflows.sqlite
│   ├── workflows.sqlite-shm
│   └── workflows.sqlite-wal
├── docs/
│   ├── archive/
│   │   ├── development_log.md
│   │   ├── phase2-plan.md
│   │   └── phase3-plan.md
│   ├── architecture.md
│   ├── deployment.md
│   ├── model_registry.md
│   ├── nlp.md
│   └── rag.md
├── reports/
│   ├── archive/
│   │   ├── huggingface_verification.json
│   │   ├── infrastructure_status.md
│   │   ├── phase2-live.json
│   │   ├── phase2-verification.md
│   │   ├── phase3-live-first-failure.json
│   │   ├── phase3-live.json
│   │   └── verification.json
│   ├── paper-query.json
│   ├── papers-report.md
│   ├── papers-workflow.json
│   ├── papers-workflow.log
│   └── restructuring.md
├── scripts/
│   ├── demo_papers.py
│   ├── init_db.py
│   ├── verify_agents.py
│   ├── verify_huggingface.py
│   ├── verify_models.py
│   ├── verify_rag.py
│   └── watch_workflow.py
├── src/
│   └── aura/
│       ├── agents/
│       │   ├── tools/
│       │   │   ├── __init__.py
│       │   │   └── dispatcher.py
│       │   ├── verification/
│       │   │   ├── __init__.py
│       │   │   └── checks.py
│       │   ├── __init__.py
│       │   ├── contracts.py
│       │   └── worker.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── application.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── exceptions.py
│       │   ├── logging_config.py
│       │   └── settings.py
│       ├── database/
│       │   ├── __init__.py
│       │   └── connection.py
│       ├── llm/
│       │   ├── providers/
│       │   │   ├── __init__.py
│       │   │   └── agentrouter.py
│       │   ├── __init__.py
│       │   ├── gateway.py
│       │   ├── registry.py
│       │   └── transport.py
│       ├── memory/
│       │   ├── __init__.py
│       │   └── manager.py
│       ├── nlp/
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── routes.py
│       │   ├── linguistics/
│       │   │   ├── __init__.py
│       │   │   └── processor.py
│       │   ├── semantic/
│       │   │   ├── __init__.py
│       │   │   └── similarity.py
│       │   ├── __init__.py
│       │   └── service.py
│       ├── orchestration/
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── routes.py
│       │   ├── graph/
│       │   │   ├── __init__.py
│       │   │   ├── nodes.py
│       │   │   ├── state.py
│       │   │   └── workflow.py
│       │   ├── workflow/
│       │   │   ├── __init__.py
│       │   │   ├── engine.py
│       │   │   └── persistence.py
│       │   └── __init__.py
│       ├── rag/
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   └── routes.py
│       │   ├── chunking/
│       │   │   ├── __init__.py
│       │   │   └── chunker.py
│       │   ├── embeddings/
│       │   │   ├── __init__.py
│       │   │   └── cache.py
│       │   ├── generation/
│       │   │   ├── __init__.py
│       │   │   ├── answers.py
│       │   │   ├── context.py
│       │   │   └── generator.py
│       │   ├── ingestion/
│       │   │   ├── __init__.py
│       │   │   └── documents.py
│       │   ├── prompts/
│       │   │   ├── __init__.py
│       │   │   └── templates.py
│       │   ├── retrieval/
│       │   │   ├── __init__.py
│       │   │   ├── evaluation.py
│       │   │   ├── ranking.py
│       │   │   └── retriever.py
│       │   ├── vectorstore/
│       │   │   ├── __init__.py
│       │   │   └── qdrant_store.py
│       │   ├── __init__.py
│       │   └── pipeline.py
│       ├── __init__.py
│       └── contracts.py
├── tests/
│   ├── evaluation/
│   │   └── test_evidence_context.py
│   ├── integration/
│   │   ├── test_agents.py
│   │   ├── test_rag.py
│   │   └── test_restructured_workflow.py
│   └── unit/
│       ├── test_agentrouter.py
│       ├── test_agentrouter_process.py
│       └── test_foundation.py
├── .env
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── main.py
├── pyproject.toml
└── requirements.txt
```

## Moves and splits

| Old path | New path |
|---|---|
| `src/aura/core.py` | `src/aura/core/{settings,exceptions,logging_config}.py; __init__.py preserves imports` |
| `src/aura/api.py` | `src/aura/api/application.py; __init__.py preserves aura.api:app` |
| `src/aura/orchestration/workflow/persistence.py` | `src/aura/memory/manager.py; old path retained as compatibility export` |
| `tests/test_agents.py` | `tests/integration/test_agents.py` |
| `tests/test_rag.py` | `tests/integration/test_rag.py` |
| `tests/test_foundation.py` | `tests/unit/test_foundation.py` |
| `tests/test_agentrouter.py` | `tests/unit/test_agentrouter.py` |

Existing tests were relocated without removing assertions. Further responsibility extractions:

- `rag/pipeline.py`: retrieval moved to `rag/retrieval/retriever.py`; answer schemas and validation to `rag/generation/answers.py`; generation to `rag/generation/generator.py`; context assembly to `rag/generation/context.py`. Pipeline methods and schema exports remain compatible.
- `orchestration/workflow/engine.py`: worker behavior moved to `agents/worker.py`; scheduling stages moved to `orchestration/graph/nodes.py`, topology to `workflow.py`, transient state to `state.py`. The engine retains budgets, task retries, cancellation, and recovery.
- SQLite connection/schema initialization extracted from memory to `database/connection.py`. `scripts/init_db.py` is idempotent. No schema migration, path migration, record deletion, or vector rebuilding occurred.
- API routes retain feature-local modules. Core settings and exception imports remain compatible. Added a real root launcher, not placeholder modules.

## Dependencies

Added declarations for `langgraph==1.2.19` and `langchain-core==1.7.3`, both already installed in the audited environment. LangGraph now controls planning, conditional task waves, and verification. LangChain-core supplies the document representation at the evidence boundary without replacing the proven LLM protocol. No existing dependency was removed or upgraded. `requirements.txt` delegates to `pyproject.toml` via `-e .`; there is no second version list.

## Validation

| Check | Result |
|---|---|
| Baseline pytest | 35 passed, 5 existing warnings |
| Original tests after initial restructuring | 35 passed, same warnings |
| Final pytest | 42 passed, same 5 PyMuPDF warnings |
| Syntax: compileall src/scripts/tests/main.py | Passed |
| Recursive module import validation | All 64 modules imported |
| OpenAPI comparison against pre-change snapshot | Entire schema identical, 23 paths |
| pip check | No broken requirements |
| pip wheel --no-deps --no-build-isolation | Wheel built successfully outside repository |
| init_db CLI, twice against temporary DATA_DIR | Passed |
| Database initialization sentinel row preservation | Passed |
| LangGraph bounded waves, retry, cancel, restart tests | Passed |
| Resume skips completed dependency task | Passed |
| RAG retrieval, ingestion, citations, API tests | Passed |
| LangChain evidence text/ID fidelity | Passed |
| Mocked AgentRouter gateway and actual subprocess boundary | Passed; endpoint, args, key handling, JSON output, token accounting, sanitized errors |
| Frontend build | Not applicable: no frontend exists |
| Live provider inference and current credits | Not tested in this restructuring |

No paid live model calls were made. Existing historical demo reports were not regenerated and do not validate the new orchestration against live services. Pytest uses isolated storage and mocked providers. Exact-quote tests are not an answer-quality or entailment benchmark.

### Persistent data

All 11 persistent protected files (`data/`, `.env`, editor settings) matched pre-edit SHA-256 fingerprints. Two transient workflow SQLite WAL/SHM sidecars present in the snapshot were no longer present at verification; SQLite manages their lifecycle. The main database remained byte-identical, and row counts and integrity were checked below. No sidecar was manually deleted. No secret values are included in this report.

- `data/embeddings.sqlite`: quick_check=ok; {"cache": 357, "documents": 4, "mutations": 0}.
- `data/workflows.sqlite`: quick_check=ok; {"goals": 3, "workflows": 3, "events": 139, "memory": 41}.
- `data/vectors/collection/aura_bge_m3_1024_v1/storage.sqlite`: quick_check=ok; {"points": 349}.

## Deleted files

No application functionality, credentials, documents, databases, tests, historical reports, or useful documentation was deleted. Old core/API source paths became packages as listed above. The following exact files were removed only as regenerable caches or artifacts generated by this run:

| File | Reason |
|---|---|
| `.pytest_cache/.gitignore` | Regenerable Python/pytest cache |
| `.pytest_cache/CACHEDIR.TAG` | Regenerable Python/pytest cache |
| `.pytest_cache/README.md` | Regenerable Python/pytest cache |
| `.pytest_cache/v/cache/nodeids` | Regenerable Python/pytest cache |
| `__pycache__/main.cpython-312.pyc` | Regenerable Python/pytest cache |
| `build/lib/aura/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/contracts.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/tools/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/tools/dispatcher.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/verification/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/verification/checks.py` | Generated by the packaging verification in this run |
| `build/lib/aura/agents/worker.py` | Generated by the packaging verification in this run |
| `build/lib/aura/api/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/api/application.py` | Generated by the packaging verification in this run |
| `build/lib/aura/contracts.py` | Generated by the packaging verification in this run |
| `build/lib/aura/core/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/core/exceptions.py` | Generated by the packaging verification in this run |
| `build/lib/aura/core/logging_config.py` | Generated by the packaging verification in this run |
| `build/lib/aura/core/settings.py` | Generated by the packaging verification in this run |
| `build/lib/aura/database/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/database/connection.py` | Generated by the packaging verification in this run |
| `build/lib/aura/llm/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/llm/gateway.py` | Generated by the packaging verification in this run |
| `build/lib/aura/llm/providers/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/llm/providers/agentrouter.py` | Generated by the packaging verification in this run |
| `build/lib/aura/llm/registry.py` | Generated by the packaging verification in this run |
| `build/lib/aura/llm/transport.py` | Generated by the packaging verification in this run |
| `build/lib/aura/memory/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/memory/manager.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/api/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/api/routes.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/linguistics/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/linguistics/processor.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/semantic/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/semantic/similarity.py` | Generated by the packaging verification in this run |
| `build/lib/aura/nlp/service.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/api/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/api/routes.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/graph/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/graph/nodes.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/graph/state.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/graph/workflow.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/workflow/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/workflow/engine.py` | Generated by the packaging verification in this run |
| `build/lib/aura/orchestration/workflow/persistence.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/api/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/api/routes.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/chunking/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/chunking/chunker.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/embeddings/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/embeddings/cache.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/generation/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/generation/answers.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/generation/context.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/generation/generator.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/ingestion/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/ingestion/documents.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/pipeline.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/prompts/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/prompts/templates.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/retrieval/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/retrieval/evaluation.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/retrieval/ranking.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/retrieval/retriever.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/vectorstore/__init__.py` | Generated by the packaging verification in this run |
| `build/lib/aura/rag/vectorstore/qdrant_store.py` | Generated by the packaging verification in this run |
| `scripts/__pycache__/demo_papers.cpython-312.pyc` | Regenerable Python/pytest cache |
| `scripts/__pycache__/init_db.cpython-312.pyc` | Regenerable Python/pytest cache |
| `scripts/__pycache__/verify_agents.cpython-312.pyc` | Regenerable Python/pytest cache |
| `scripts/__pycache__/verify_huggingface.cpython-312.pyc` | Regenerable Python/pytest cache |
| `scripts/__pycache__/verify_models.cpython-312.pyc` | Regenerable Python/pytest cache |
| `scripts/__pycache__/verify_rag.cpython-312.pyc` | Regenerable Python/pytest cache |
| `scripts/__pycache__/watch_workflow.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/__pycache__/api.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/__pycache__/contracts.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/__pycache__/core.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/__pycache__/contracts.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/__pycache__/worker.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/tools/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/tools/__pycache__/dispatcher.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/verification/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/agents/verification/__pycache__/checks.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/api/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/api/__pycache__/application.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/core/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/core/__pycache__/exceptions.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/core/__pycache__/logging_config.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/core/__pycache__/settings.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/database/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/database/__pycache__/connection.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/llm/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/llm/__pycache__/gateway.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/llm/__pycache__/registry.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/llm/__pycache__/transport.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/llm/providers/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/llm/providers/__pycache__/agentrouter.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/memory/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/memory/__pycache__/manager.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/__pycache__/service.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/api/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/api/__pycache__/routes.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/linguistics/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/linguistics/__pycache__/processor.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/semantic/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/nlp/semantic/__pycache__/similarity.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/api/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/api/__pycache__/routes.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/graph/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/graph/__pycache__/nodes.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/graph/__pycache__/state.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/graph/__pycache__/workflow.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/workflow/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/workflow/__pycache__/engine.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/orchestration/workflow/__pycache__/persistence.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/__pycache__/pipeline.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/api/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/api/__pycache__/routes.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/chunking/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/chunking/__pycache__/chunker.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/embeddings/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/embeddings/__pycache__/cache.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/generation/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/generation/__pycache__/answers.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/generation/__pycache__/context.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/generation/__pycache__/generator.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/ingestion/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/ingestion/__pycache__/documents.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/prompts/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/prompts/__pycache__/templates.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/retrieval/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/retrieval/__pycache__/evaluation.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/retrieval/__pycache__/ranking.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/retrieval/__pycache__/retriever.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/vectorstore/__pycache__/__init__.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura/rag/vectorstore/__pycache__/qdrant_store.cpython-312.pyc` | Regenerable Python/pytest cache |
| `src/aura_model_infrastructure.egg-info/PKG-INFO` | Generated by the packaging verification in this run |
| `src/aura_model_infrastructure.egg-info/SOURCES.txt` | Generated by the packaging verification in this run |
| `src/aura_model_infrastructure.egg-info/dependency_links.txt` | Generated by the packaging verification in this run |
| `src/aura_model_infrastructure.egg-info/requires.txt` | Generated by the packaging verification in this run |
| `src/aura_model_infrastructure.egg-info/top_level.txt` | Generated by the packaging verification in this run |
| `tests/__pycache__/test_agentrouter.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/__pycache__/test_agents.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/__pycache__/test_foundation.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/__pycache__/test_rag.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/evaluation/__pycache__/test_evidence_context.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/evaluation/__pycache__/test_evidence_context.cpython-312.pyc` | Regenerable Python/pytest cache |
| `tests/integration/__pycache__/test_agents.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/integration/__pycache__/test_agents.cpython-312.pyc` | Regenerable Python/pytest cache |
| `tests/integration/__pycache__/test_rag.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/integration/__pycache__/test_rag.cpython-312.pyc` | Regenerable Python/pytest cache |
| `tests/integration/__pycache__/test_restructured_workflow.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/integration/__pycache__/test_restructured_workflow.cpython-312.pyc` | Regenerable Python/pytest cache |
| `tests/unit/__pycache__/test_agentrouter.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/unit/__pycache__/test_agentrouter.cpython-312.pyc` | Regenerable Python/pytest cache |
| `tests/unit/__pycache__/test_agentrouter_process.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/unit/__pycache__/test_agentrouter_process.cpython-312.pyc` | Regenerable Python/pytest cache |
| `tests/unit/__pycache__/test_foundation.cpython-312-pytest-9.1.1.pyc` | Regenerable Python/pytest cache |
| `tests/unit/__pycache__/test_foundation.cpython-312.pyc` | Regenerable Python/pytest cache |

## Remaining issues and deliberate limits

- Native LangGraph interrupts/checkpointers are not implemented. Existing SQLite recovery remains authoritative; it reconstructs task-wave execution without duplicating history.
- No authentication was present; project scoping is retained, but is not a multi-user security boundary. Keep the development API local.
- OpenCode request token caps are prompt instructions rather than guaranteed hard provider limits; generation is buffered. Provider protocol and model IDs were preserved.
- Existing AgentRouter subprocess cancellation cleanup is incomplete; timeout kills the process, but task cancellation may leave the child running. This remains a targeted follow-up rather than an unrelated transport rewrite.
- Citation verification checks identity and exact quotes, not semantic entailment. Multi-document search still has the existing first-five-candidates behavior in the agent dispatcher.
- SQLite/Qdrant operations retain the existing mutation journal, not a cross-store transaction.
- Optional spaCy model installation controls full linguistic annotations. OCR, intent classification, language detection, and a frontend remain unimplemented; no placeholders were created.
- Historical docs and reports were retained because their removal would discard unique work. No ambiguous deletion is pending or required to use this structure.
- Baseline source uses compact formatting in several modules; this refactor prioritizes behavior and boundaries over a repository-wide style rewrite.

See `docs/architecture.md` for runtime data flow and `README.md` for setup, environment variables, initialization, testing, and live workflow monitoring.
