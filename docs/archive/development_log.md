# Development log — 2026-11-04

Stages 1–2: audited empty repository; configured Python package, contracts, transport, registry and DI. Stage 3: live model discovery and approved provider clients. Stage 4: operational embeddings/reranking; typed OCR interface explicitly unavailable without verified endpoint. Specialist NLP backbones deferred pending requirements. Stage 5: 16 offline pytest tests passed; wheel install passed; GPT-OSS and Cloudflare live inference passed; Gemini returned 503. Actual Uvicorn startup and all three HTTP endpoints returned 200; readiness correctly remained unverified in the new API process. Temporary server stopped after checks. Stage 6: architecture, responsibility map, model matrix, setup and verification documentation written. Git initialized; .env ignored and unchanged. Secret scan passed across 18 implementation/test/document/report files.

Remaining limitations: no hosted OCR endpoint, no HF free-credit proof, Gemini inference unavailable during test, no tool-call or multimodal request contract yet. Account billing settings remain an external prerequisite for strict zero-cost usage. No paid resource provisioning performed. No main application pipeline implemented.


HF follow-up: registered Qwen/Qwen3-14B, meta-llama/Llama-3.1-8B-Instruct and openai/gpt-oss-20b. Real Qwen inference returned HTTP 402. Remaining model tests skipped because account credits are exhausted. No model marked verified, no credit purchase or endpoint deployment. Repeat with PYTHONPATH=src python3 scripts/verify_huggingface.py after free credits reset.


Phase 2: audited baseline (17 tests passed), implemented ingestion/chunking/storage/retrieval/generation/NLP/API, then validated 27 tests. Real RAG passed with valid exact-quote citation and restart persistence. Trained spaCy NER passed. Package rebuild passed. Detailed limitations and file map in reports/phase2-verification.md.
