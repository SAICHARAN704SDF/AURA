"""Browser integration fixture. Only external embedding and reranking requests are replaced."""
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import tempfile
import os
import hashlib
import re

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/src"))
from aura.api import create_app
from aura.core import Settings
import uvicorn

with tempfile.TemporaryDirectory(prefix="researchos-browser-") as directory:
    live = os.getenv("RESEARCHOS_LIVE") == "1"
    app = create_app(Settings(_env_file=ROOT / ".env" if live else None, data_dir=directory))
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with original(app):
            async def embed(texts):
                vectors = []
                for text in texts:
                    vector = [0.0] * 1024
                    for token in re.findall(r"\w+", text.lower()):
                        index = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") % 1024
                        vector[index] += 1
                    vectors.append(vector)
                return vectors

            async def rerank(question, passages):
                words = set(question.lower().split())
                return [{"id": i, "score": len(words & set(text.lower().split()))} for i, text in enumerate(passages)]

            if not live:
                app.state.gateway.embed = embed
                app.state.gateway.rerank = rerank
            yield

    app.router.lifespan_context = lifespan
    uvicorn.run(app, host="127.0.0.1", port=18135, access_log=False)
