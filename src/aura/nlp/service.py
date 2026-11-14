"""Public NLP service composing linguistic and semantic analysis."""
from aura.observability.events import traced, emit, span
from .linguistics.processor import LinguisticProcessor
from .semantic.similarity import similarity


class NLP:
    def __init__(self, embedding):
        self.embedding = embedding
        self.linguistics = LinguisticProcessor()

    def status(self):
        return self.linguistics.status()

    @traced('nlp_linguistics')
    def analyze(self, text):
        return self.linguistics.analyze(text)

    @traced('semantic_similarity')
    async def similarity(self, first, second):
        return await similarity(self.embedding, first, second)
