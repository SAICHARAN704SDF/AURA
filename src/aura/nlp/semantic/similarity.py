"""Cloud embedding based text similarity."""
from aura.rag.retrieval.ranking import cosine


async def similarity(embedding, first, second):
    vectors = await embedding.embed([first, second])
    return {'cosine': cosine(*vectors), 'model': embedding.model}
