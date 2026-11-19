"""
FILE: backend/src/aura/nlp/service.py
PURPOSE: Expose linguistic analysis and embedding-based similarity.
MAIN RESPONSIBILITY: Nlp Service.
INPUTS: Text or two texts and the shared embedding service.
OUTPUTS: Annotations or similarity result.
IMPORTANT FUNCTIONS / CLASSES: NLP.
CONNECTED MODULES: aura.observability.events.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py.
PRESENTATION EXPLANATION: "NLP has explicit modes; it is not automatically executed for every report."
"""
# PRESENTATION SECTION: NLP SERVICE
from aura.observability.events import traced, emit, span
from .linguistics.processor import LinguisticProcessor
from .semantic.similarity import similarity


class NLP:
    """Facade combining local linguistic annotations with shared hosted embedding similarity. API and tool dispatch reuse this service instead of duplicating NLP preprocessing."""
    def __init__(self, embedding, model="en_core_web_sm", terms=None):
        self.embedding = embedding
        self.linguistics = LinguisticProcessor(model, terms)

    def status(self):
        return self.linguistics.status()

    @traced('nlp_linguistics')
    def analyze(self, text):
        return self.linguistics.analyze(text)

    @traced('semantic_similarity')
    async def similarity(self, first, second):
        return await similarity(self.embedding, first, second)
