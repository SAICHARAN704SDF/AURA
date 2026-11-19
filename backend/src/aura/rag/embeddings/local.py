"""Offline passage encoder. Preload the public weights before running without network."""
import asyncio
from aura.core import ServiceError


class LocalMiniLM:
    model = 'sentence-transformers/all-MiniLM-L6-v2'
    dimension = 384

    def __init__(self):
        self.encoder = None

    def _encode(self, texts):
        if self.encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer(self.model, device='cpu', local_files_only=True)
            except (OSError, ImportError, ValueError):
                raise ServiceError('local_encoder_unavailable') from None
        return self.encoder.encode(texts,normalize_embeddings=True,show_progress_bar=False).tolist()

    async def embed(self, texts):
        return await asyncio.to_thread(self._encode,texts)
