# NLP

POST /nlp/analyze accepts text. Lazy en_core_web_sm supplies tokenization, sentences, POS, lemmas, dependencies and named entities. Installed model: 3.8.0, 12.8 MB download; no transformer weights. If absent, explicit trained_pipeline=false accompanies tokenization/sentences only. Install using python3 -m spacy download en_core_web_sm.

POST /nlp/similarity accepts first and second (each at most 2000 characters), uses the shared cached Cloudflare embedding service, and returns cosine similarity. GET /nlp/status exposes loaded state.

Classification is unavailable: DeBERTa-v3, ModernBERT and RoBERTa are backbone families, not a selected domain label taxonomy. No task-specific free hosted checkpoint has passed classification verification. No redundant models deployed. Relation extraction is also explicitly unavailable rather than claimed as transformer inference.
