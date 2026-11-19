"""
FILE: backend/src/aura/rag/chunking/chunker.py
PURPOSE: Split page text into overlapping source-preserving passages.
MAIN RESPONSIBILITY: Text Chunking.
INPUTS: Document, character size and overlap.
OUTPUTS: List of Chunk records with original offsets.
IMPORTANT FUNCTIONS / CLASSES: chunks.
CONNECTED MODULES: aura.observability.events, aura.core, aura.rag.ingestion.documents.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py.
PRESENTATION EXPLANATION: "Chunks keep page and character positions; the splitter prefers newline boundaries."
"""
# PRESENTATION SECTION: TEXT CHUNKING
from aura.observability.events import traced, emit, span
import re
import uuid
from aura.core import ServiceError
from aura.rag.ingestion.documents import Document, Chunk, digest

@traced('chunking')
def chunks(doc: Document, size: int=1200, overlap: int=150, strategy: str='recursive') -> list[Chunk]:
    """Purpose: Chunking.
    
    Inputs: Document, size=1200 and overlap=150 characters.
    Process and rationale: Split each page, prefer newlines in the latter half of a window and preserve literal offsets; overlapping context reduces boundary loss.
    Returns: Source-labelled Chunk list.
    """
    if not 100<=size<=1800 or not 0<=overlap<size: raise ServiceError('invalid_chunk_config')
    if strategy not in {'fixed', 'recursive', 'sentence', 'structure'}:
        raise ServiceError('invalid_strategy')
    result=[]
    for p in doc.pages:
        start=0
        while start<len(p.text):
            end=min(start+size,len(p.text))
            if end < len(p.text) and strategy != 'fixed':
                window = p.text[start:end]
                boundaries = {
                    'recursive': r'\n',
                    'sentence': r'(?<=[.!?])\s+',
                    'structure': r'\n(?=#+\s)|\n\s*\n',
                }
                cuts = [m.end() for m in re.finditer(boundaries[strategy], window)
                        if m.end() >= size // 2]
                if cuts:
                    end = start + cuts[-1]
            text=p.text[start:end]
            if text.strip():
                h=digest(text.encode())
                result.append(Chunk(id=str(uuid.uuid5(uuid.NAMESPACE_URL,f'{doc.id}:{p.number}:{start}:{end}')),document_id=doc.id,filename=doc.filename,page=p.number,start=start,end=end,text=text,content_hash=h))
            if end==len(p.text): break
            start=max(start+1,end-overlap)
    return result

async def semantic_chunks(doc, embed, threshold=0.8):
    """Merge adjacent sentence blocks when their embeddings agree, retaining exact source spans."""
    from aura.rag.retrieval.ranking import cosine
    if not -1 <= threshold <= 1:
        raise ServiceError('invalid_semantic_threshold')
    base = chunks(doc, 600, 0, strategy='sentence')
    if len(base) > 2000:
        raise ServiceError('chunk_limit')
    vectors = await embed([block.text for block in base]) if base else []
    pages = {page.number: page.text for page in doc.pages}
    merged = []
    for i, block in enumerate(base):
        if merged and merged[-1].page == block.page and block.end - merged[-1].start <= 1800 and cosine(vectors[i-1], vectors[i]) > threshold:
            first = merged.pop()
            text = pages[block.page][first.start:block.end]
            block = first.model_copy(update={
                'end': block.end, 'text': text, 'content_hash': digest(text.encode()),
                'id': str(uuid.uuid5(uuid.NAMESPACE_URL, f'{doc.id}:{block.page}:{first.start}:{block.end}'))
            })
        merged.append(block)
    return merged
