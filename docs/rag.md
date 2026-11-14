# RAG

Upload PDF/TXT/Markdown/UTF-8 CSV through POST /documents/upload. Maximum 5 MiB, 200 PDF pages, one million extracted characters and 1000 chunks. Filenames are labels, never filesystem destinations. Raw files are not retained. Exact byte hashes identify duplicate documents. CSV offsets refer to the extracted row representation; PDF offsets refer to extracted page text, not PDF byte offsets.

Recursive chunking defaults to 1200 characters with 150 overlap. Semantic mode embeds adjacent 600-character blocks and merges similar neighbors up to 1800 characters. It is a paragraph-scale similarity heuristic, not a learned segmentation model. A semantic rate-limit failure falls back to recursive chunking, but final indexing still needs available embedding quota; it never invents vectors.

BGE-M3 vectors are validated at 1024 dimensions and cached in SQLite by model and text hash. Qdrant persists vectors and chunk metadata in data/vectors. QDRANT_URL reuses a configured server; default requires no server. Collection name pins model and dimension. Do not change models in place. One application process owns local Qdrant; use one Uvicorn worker.

Dense cosine retrieval and BM25 keyword retrieval are fused with RRF, deduplicated and reranked by Cloudflare. Sparse ranking reads current Qdrant payloads, so deletion cannot leave a separate stale BM25 index. This is suitable for small corpora; it currently scans the corpus in memory and needs an indexed sparse implementation for large collections.

Groq receives a system instruction and bounded JSON evidence. Exact chunk IDs and quotes are verified after structured answer validation. Documents never trigger tool execution. Instruction isolation reduces injection risk but cannot guarantee an LLM ignores every malicious passage. Citation existence and quote matching do not establish entailment.

POST /retrieval/search and /rag/query take question and optional document_id. GET /documents, GET/DELETE /documents/{id}, GET /rag/status expose persistence and status. No arbitrary file reads. Scanned pages remain explicitly requires_ocr; native pages remain usable. OCR unavailable and classification unavailable are honest statuses.

Evaluation includes deterministic precision@k, recall@k and MRR functions, offline fixtures and scripts/verify_rag.py for real cloud acceptance. Character counts are not token quotas; remaining provider allowance is unknown.

Limits: uploads are bounded but buffered; indexing is not transactional across SQLite and Qdrant on abrupt process termination. Cleanup handles ordinary failures. No tenant authentication or multi-user isolation; bind to localhost. No table structure extraction beyond native text/CSV, no calibrated answer-faithfulness metric.
