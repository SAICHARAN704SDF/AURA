"""
FILE: backend/src/aura/nlp/semantic/similarity.py
PURPOSE: Compare two texts using shared embeddings and cosine similarity.
MAIN RESPONSIBILITY: Semantic Similarity.
INPUTS: Embedding service and two text strings.
OUTPUTS: Cosine score and embedding model identifier.
IMPORTANT FUNCTIONS / CLASSES: similarity.
CONNECTED MODULES: aura.rag.retrieval.ranking, aura.observability.events.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "This compares vector directions; similar text is not necessarily logically equivalent."
"""
# PRESENTATION SECTION: SEMANTIC SIMILARITY
from aura.rag.retrieval.ranking import cosine
from aura.observability.events import span


async def similarity(embedding, first, second):
    """Purpose: Semantic text comparison.
    
    Inputs: Shared embedding service and two strings.
    Process and rationale: Embed both texts through the common cache and call cosine under a traced span.
    Returns: Dictionary containing cosine score and embedding model.
    """
    vectors = await embedding.embed([first, second])
    with span('cosine_similarity'):
        score=cosine(*vectors)
    return {'cosine': score, 'model': embedding.model}
