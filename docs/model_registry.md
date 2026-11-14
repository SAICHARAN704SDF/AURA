# Deployment matrix

| Capability | Route | Status |
|---|---|---|
| Text/JSON | Groq GPT-OSS-120B | Real text inference passed; schema validation covered offline |
| Text/JSON | AgentRouter GPT-5.6 Sol via OpenCode | Live structured inference, cited RAG answer, and four-paper agent report passed |
| Text/JSON | Gemini Flash candidates | Discovery works; recent inference returned 503 or timed out |
| Embeddings | Cloudflare BGE-M3 | Real inference passed |
| Reranking | Cloudflare BGE-reranker-base | Real inference passed |
| HF Inference Providers | Catalog discovery | Qwen3-14B attempted: HTTP 402; Qwen, Llama-3.1-8B and GPT-OSS-20B registered, none inference-verified |
| OCR | Xiaomi/PaddleOCR via hosted runtime | No endpoint deployed or verified; interface reports unavailable |

Discovery lists provider-advertised models, not an entitlement or a guarantee of free usage. Generation uses the explicit registry allowlist. Do not treat the historical research list as proven deployment availability. Gemini older IDs are compatibility candidates only when actually discovered. No weights are downloaded.

Official references: https://console.groq.com/docs/rate-limits ; https://ai.google.dev/gemini-api/docs/pricing ; https://developers.cloudflare.com/workers-ai/platform/pricing/ ; https://huggingface.co/docs/inference-providers/en/pricing ; https://huggingface.co/docs/hub/spaces-zerogpu .

Phase 2 revalidation: GPT-OSS grounded generation, BGE-M3 embeddings and BGE-reranker-base all passed real document integration. en_core_web_sm 3.8.0 installed for lightweight linguistic processing. Heavy classifier backbones and OCR remain unavailable.
