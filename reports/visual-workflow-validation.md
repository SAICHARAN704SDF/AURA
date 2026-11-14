# Visual workflow update — 2026-11-14

Implemented a workflow-first dashboard with a paper/prompt sidebar, dotted canvas, dependency arrows including branches/joins, horizontal/vertical orientation, focus view, selected-step details, live statuses, technical logs, downloads, and explicitly labelled saved-event replay. Replay uses history GET requests and makes no inference calls.

Default generation now uses Groq openai/gpt-oss-20b with low reasoning effort. AgentRouter credentials and adapter are preserved for explicit selection. There is no automatic larger-model fallback. Dashboard agent runs have limits of 6 LLM calls, 8 tool calls, 180 seconds and concurrency 1. Provider quotas are separate and actual dollar balance is unknown.

Validation:
- Python suite: 56 passed; five existing PyMuPDF/SWIG deprecation warnings.
- JavaScript dependency-layout test: branch, join, out-of-order plan, orientation, and answer path passed using DOM stubs.
- JavaScript syntax and Python compilation passed.
- pip check: no broken requirements.
- Small-model live cited paper answer passed in 1.98 seconds with 1,860 reported tokens (small-model-validation.json).
- Live agent-report experiments failed with provider tool-use errors, structured-output errors, and one rate limit. All outcomes remain in small-model-*.json; none is presented as successful. Action responses now use a forced data-envelope function, and prompts avoid unrelated examples. Full report reliability remains unverified with the final configuration. No more paid report experiments were run to conserve quota.
- Browser access was disabled in Work settings. The new layout has NOT received a real browser visual or end-to-end interaction check. DOM tests are not a substitute for that check.

No dependencies were added. No credentials or persistent records were deleted. The saved replay may show a previous provider/model; event details preserve that historical identity.
