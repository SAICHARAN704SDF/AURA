# Student demonstration

Use Python 3.12 and Node only for optional JavaScript syntax checks. No frontend build is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m spacy download en_core_web_sm
# On a NEW checkout only, copy .env.example to .env and supply your own keys.
npm install --global opencode-ai@1.19.5
python scripts/init_db.py
python main.py
```

Set `AURA_LLM_PROVIDER=agentrouter`, `AGENTROUTER_MODEL=gpt-5.6-sol`, your AgentRouter key, and Cloudflare account ID/token in `.env`. The provider model is a configured identifier; availability depends on the account. Never commit `.env`. Run from the project root, with one server worker for local Qdrant. No cloud provider balance is inferred by AURA.

Open http://127.0.0.1:8000. Upload an authorized paper, select its checkbox, and demonstrate:

1. Cited answer: “Summarize this paper's problem, dataset, approach and reported result. Cite exact quotes.”
2. Cited answer: “What methods and evaluation scores are reported? Distinguish evidence from unsupported claims.”
3. Agent report: “Write a concise review of the paper's dataset, methods, results and limitations using exact evidence.”

During generation inspect the event timeline: cache hits/misses, Cloudflare requests, retrieval/rerank, context assembly and model usage. An agent report also shows planning, task dependencies, observe/act steps, and final verification. Expand events and download the trace. Download Markdown, Text and JSON output. Use Previous runs to reopen a saved report. Report failures are preserved rather than represented as success.

Language analysis processes supplied text with spaCy; semantic similarity compares two texts with hosted embeddings. These are separate modes and do not run automatically for every question.

## Recheck

```sh
python -m pytest -q
python -m compileall -q src scripts tests main.py
node --check frontend/app.js
python -m pip check
```

Tests use mocks and temporary databases. Live requests consume provider quota. Retrieval fixtures in `tests/evaluation/fixtures/` are synthetic and measure lexical relevance and quotation validity, not full answer quality. See the final validation report for live paper results.
