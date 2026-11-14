# Infrastructure verification

Real checks executed 2026-11-04. No paid resources provisioned.

- groq: 11 discovered models; authentication=True; error=None
- gemini: 50 discovered models; authentication=True; error=None
- huggingface: 126 discovered models; authentication=True; error=None
- cloudflare: 73 discovered models; authentication=True; error=None

Inference results:
{
  "groq": {
    "model": "openai/gpt-oss-120b",
    "success": true,
    "tokens": 114,
    "seconds": 0.494
  },
  "gemini": {
    "model": "gemini-3.8-flash",
    "error": "http_503"
  },
  "embed": {
    "success": true,
    "items": 1
  },
  "rerank": {
    "success": true,
    "items": 2
  }
}

Observed process RSS: 54.73 MiB; not peak RAM or total system memory.

Package wheel built and installed into .packages with --no-deps; installed dependencies reused. OCR remains unavailable. Gemini inference is blocked by provider 503. HF generation is not enabled. These are partial capability limitations, not successful end-to-end OCR or all-provider inference.
Final offline suite: 16 passed in 0.80s. Actual Uvicorn server started; /health, /models and /providers/status each returned HTTP 200. Health correctly reported unverified because verification is process-local. Server RSS sample 63.69 MiB. Temporary server shut down cleanly. Git initialized, .env ignored. Source secret scan passed.


HF follow-up: registered Qwen/Qwen3-14B, meta-llama/Llama-3.1-8B-Instruct and openai/gpt-oss-20b. Real Qwen inference returned HTTP 402. Remaining model tests skipped because account credits are exhausted. No model marked verified, no credit purchase or endpoint deployment. Repeat with PYTHONPATH=src python3 scripts/verify_huggingface.py after free credits reset.
