# Student demonstration

Use Python 3.12 and Node only for optional JavaScript syntax checks. No frontend build is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m spacy download en_core_web_sm
# On a NEW checkout only, copy .env.example to .env and supply your own keys.
python scripts/init_db.py
python main.py
```

Set `AURA_LLM_PROVIDER=groq`, `GROQ_MODEL=openai/gpt-oss-20b`, your Groq key, and Cloudflare account ID/token in `.env`. This is the small-model default. AgentRouter remains optional; its OpenCode CLI must be installed separately when selected. The provider model is a configured identifier; availability depends on the account. Never commit `.env`. Run from the project root, with one server worker for local Qdrant. No cloud provider balance is inferred by AURA.

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
node tests/unit/test_workflow_canvas.cjs
python -m pip check
```

Tests use mocks and temporary databases. Live requests consume provider quota. Retrieval fixtures in `tests/evaluation/fixtures/` are synthetic and measure lexical relevance and quotation validity, not full answer quality. See the final validation report for live paper results.

## Explain it to a class

The main page has four steps: add a paper, ask a question, watch the steps, and read/download the answer. Click a workflow card for its plain-language explanation. Purple means working, green means finished, and an attention label means a failure. Technical details stay collapsed until needed.

Start with **Show saved example · no credits** to replay recorded real agent events without making new AI calls. It is visibly labelled REPLAY, not live generation. Then select **Quick answer · fewer AI calls**, select a paper, and ask about its reported results. Detailed reports use planning and research/analysis agents and therefore consume more calls. Dashboard reports are limited to 6 model calls and 8 tool calls; this is a call limit, not a dollar budget. Cloudflare embedding/reranking requests have their own quota.

A smaller model does not guarantee fewer tokens for every prompt. This configuration uses low reasoning effort, bounded context, and no automatic larger-model fallback. AURA shows provider-reported tokens, not account balances or a promised price.

Use **Horizontal view** to spread a long graph across the canvas, or **Focus workflow** to hide the sidebar during a presentation. The arrows represent actual plan dependencies, including branches and joins. Select a card to inspect its explanation and latest event. Expand the logs below the canvas for server requests and usage. The graph is a monitor, not a drag-and-drop workflow editor.

Current limitation: quick cited answers have been validated with the 20B model. Live detailed-report tests have encountered structured-response and provider rate-limit failures; they are not yet validated as reliable with this model. Use the clearly labelled saved-run replay for a dependable agent-workflow demonstration. No large-model fallback is enabled.
