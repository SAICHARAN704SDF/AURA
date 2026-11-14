# Dashboard validation — 2026-11-10

Implemented local frontend, upload and document selection, agent reports, cited answers, NLP analysis, semantic similarity, real event-based stage visualization, dependency cards, event filtering/export, usage metrics, saved workflow selection/resume/cancel, and Markdown/Text/JSON downloads.

Backend additions: bounded request/workflow telemetry; stage spans and cache/retrieval/NLP details; sanitized status and history APIs; static frontend serving; AgentRouter subprocess cleanup on cancellation. Existing foundation API test now uses temporary storage rather than the real data directory. Provider/model selection and storage schema are unchanged.

Checks:
- 46 pytest tests passed, with the five existing PyMuPDF SWIG warnings.
- JavaScript syntax: `node --check frontend/app.js` passed.
- Python compilation: `python3 -m compileall -q src scripts tests main.py` passed.
- Wheel build with frontend assets passed.
- Live local server returned HTTP 200 for the dashboard.
- Mocked upload → embedding → storage → retrieval → answer tests passed with exact evidence validation and trace correlation.
- Failure telemetry, bounded buffer rollover, project-scoped history, LangGraph stage events, and subprocess cancellation checks passed.
- Browser preview unavailable: computer-use host reported unavailable. No browser layout, download-click, or end-to-end browser assertion is claimed.
- No paid model generation was executed during this validation. Startup provider discovery may contact configured providers; it does not run inference.

Limits: detailed telemetry is transient (5,000 events), lifecycle/report data persists in SQLite; one local Qdrant server worker; no authentication; single-request NLP/RAG has no cancellation endpoint; no model token streaming; provider credit/cost and tunnel state are not measurable by the existing integration. Cloudflare Tunnel is not started or configured. The UI shows these unknowns explicitly.
