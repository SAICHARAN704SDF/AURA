# Final validation — 14 November 2026

## Results

54 automated tests pass; five existing PyMuPDF SWIG deprecation warnings remain. Python compilation, JavaScript syntax, `pip check`, and wheel packaging pass. The wheel includes all three frontend assets.

The full browser journey was tested through the in-app browser against the real localhost server, with actual AgentRouter/OpenCode and Cloudflare calls. No mock was used for the following three paper runs:

| Test | Result | Reported tokens | Evidence |
|---|---|---:|---|
| Paper summary | Completed; citations validated; missing numerical detail disclosed | 9,353 | `prompt-1.json`, `trace-1.json` |
| Table 1 model comparison | Completed; validation metrics and exact quotes returned | 8,309 | `prompt-2.json`, `trace-2.json` |
| Agent research review | COMPLETED / verification PASS, 63.7 seconds, 4 LLM calls, 1 tool call | 36,056 | `prompt-3.json`, `trace-3.json`, `report.md`, `report.txt` |

Total reported generation usage across these runs: 53,718 tokens, including OpenCode prompt overhead. Dollar cost and remaining balance are unknown. Source: `FIRE_PROMID_Misinformation_dashboard.pdf`, 8 pages, previously indexed as 23 chunks. Re-upload in the browser correctly recognized the duplicate and selected it without rebuilding the index.

Browser checks passed: upload/duplicate feedback, retained document selection, prompt input, real timeline updates, model usage, dependency cards, JSON and trace downloads, Markdown and Text report downloads, saved report reopening, restored elapsed time, and status refresh. No browser console errors were observed. A screenshot is saved as `dashboard.jpg`.

Additional live UI checks: spaCy analysis returned tokens, sentences, POS, lemmas, dependencies and entities using the trained pipeline; semantic similarity returned cosine 0.8039005838 for two related misinformation sentences using BGE-M3. These operations worked, but individual model predictions are not guaranteed correct (for example the entity model labeled “Alice” as ORG in this example).

## Reliability changes

- Prompt views deduplicate retrieved chunks and bound text/previous results under the context limit. Full observations stay in SQLite for verification.
- Planner instructions explain that listed task tools are required. Premature finish gets explicit remaining-tool feedback within the step budget.
- Agent timeout is 90 seconds, while workflow/global budgets remain enforced.
- Invalid inherited citations are rejected rather than silently discarded; valid literal subquotes are accepted.
- Cited-answer generation retries exact-quote validation once, counting usage from both attempts.
- Regression tests cover bounded context, required-tool recovery, invalid citations, cancellation, budgets, scope, and persistence.
- Four synthetic evaluation queries cover top-ranked lexical relevance, expected literal answers, missing evidence, and rejection of invented quotations. This is a small correctness benchmark, not a statistical LLM-quality evaluation.

## Important limits

PASS establishes exact quotation/provenance and explicit numeric checks, not semantic entailment. The final report retrieved three chunks and correctly disclosed missing dataset/preprocessing coverage; those details may exist elsewhere in the paper. Report exhaustiveness and retrieval coverage remain quality limitations. The UI returns an audit-style report with intermediate task outputs, so sections may repeat.

The system remains a local student MVP, not a production multi-user service. No authentication, OCR, hosted deployment, managed tunnel, provider balance lookup, token streaming, or native LangGraph interrupt/checkpointer is claimed. Detailed spans are limited to a 5,000-event memory buffer; workflow records persist. The previous failed runs remain available in historical reports for comparison.

GitHub publication includes source, tests, documentation, and these validation artifacts. Credentials, PDFs, vector indexes and local databases are excluded. GitHub Actions provides a separate clean-run check after publication; its result is reported in the final handoff.
