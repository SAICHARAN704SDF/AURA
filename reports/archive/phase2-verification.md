# Phase 2 verification

Implemented native PDF/TXT/Markdown/CSV extraction, scanned-page flags, hash deduplication, stable chunks with offsets, semantic boundary heuristic, cached 1024-dimensional BGE-M3 embeddings, persistent Qdrant, BM25/RRF hybrid retrieval, cloud reranking with explicit fallback status, grounded Groq JSON answers, citation identity/exact-quote checks, spaCy analysis and semantic similarity endpoints.

Tests: 27 passed in 2.95s, including all 17 Phase 1 tests. Five PyMuPDF SWIG deprecation warnings. Package wheel build and installation passed. API tests cover upload, retrieval, read, delete and validation.

Real cloud result:
```json
{
  "rss_before_mb": 96.515625,
  "document_id": "6cc24bc5-b8a5-5abc-939c-03abac603c1c",
  "answer": {
    "answer": "2.4 meters",
    "insufficient_evidence": false,
    "citations": [
      {
        "chunk_id": "60d9fb8a-8ac4-5e8e-b151-dc82669d9526",
        "quote": "Its telescope mirror has a diameter of 2.4 meters."
      }
    ]
  },
  "reranked": true,
  "usage": 730,
  "rss_after_ingest_mb": 102.515625,
  "embedding_calls": 2,
  "persistence_passed": true,
  "seconds": 2.867231375001211
}
```

Separate trained spaCy check returned Apple/ORG, John Smith/PERSON, London/GPE; process RSS 347.91 MiB. RAG RSS samples 96.52 to 102.52 MiB are snapshots, not peaks. End-to-end latency 2.87 seconds. Persistence verified after closing/reopening Qdrant and SQLite. No paid resources provisioned. Account-side free-plan quotas still apply.

Created files:
- src/aura/rag/__init__.py
- src/aura/rag/documents.py
- src/aura/rag/storage.py
- src/aura/rag/pipeline.py
- src/aura/rag/routes.py
- src/aura/rag/evaluation.py
- src/aura/nlp.py
- tests/test_rag.py
- scripts/verify_rag.py
- docs/phase2-plan.md
- docs/rag.md
- docs/nlp.md
- docs/deployment.md

Modified files:
- src/aura/api.py
- src/aura/core.py
- src/aura/gateway.py
- pyproject.toml
- .gitignore
- README.md
- docs/architecture.md
- docs/model_registry.md
- docs/development_log.md

Generated reports: reports/phase2-live.json and reports/phase2-verification.md.

Unsupported: OCR, task-specific classification, relation extraction, table structure reconstruction, entailment verification. Known limitations: sparse corpus scan; local single-process storage; no cross-store crash transaction; unauthenticated localhost API; semantic quota fallback still needs final embedding quota. API outputs currently serialize typed internal models and dictionaries rather than declaring response schemas for every route. No claim of production hardening or complete coverage of every requested edge case.

Dependencies added: qdrant-client 1.20.0, pymupdf 1.28.2, spacy 3.8.18, python-multipart 0.0.33; installed en_core_web_sm 3.8.0. No transformer, LLM or OCR weights loaded locally.
