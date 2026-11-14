# Local deployment

Python 3.12: pip install -e '.[test]'; python3 -m spacy download en_core_web_sm.
Keep .env private and all provider accounts on free plans. Run make test, then PYTHONPATH=src python3 scripts/verify_rag.py for opt-in real cloud tests. Start make serve with one worker. DATA_DIR defaults to data; QDRANT_URL optionally points at an existing server. Never expose this unauthenticated development API publicly.

The inherited MAX_RSS_MB=512 guard is a process safety threshold, configurable through environment settings. It reports memory_limit; it is not an OS-enforced cap or a claim that 512 MiB is required. Measured RAG memory is substantially lower. spaCy increases process RSS when initialized. No local LLM, embedding or OCR inference occurs.
