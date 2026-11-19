"""
FILE: backend/src/aura/rag/retrieval/retriever.py
PURPOSE: Fuse semantic and lexical rankings, deduplicate and optionally rerank.
MAIN RESPONSIBILITY: Hybrid Retrieval.
INPUTS: Pipeline, question, top-k and optional document ID.
OUTPUTS: Ranked chunks plus reranking status and timing.
IMPORTANT FUNCTIONS / CLASSES: search.
CONNECTED MODULES: aura.observability.events, aura.core.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py.
PRESENTATION EXPLANATION: "Combining meaning-based and word-based search helps retrieve evidence before generation."
"""
# PRESENTATION SECTION: HYBRID RETRIEVAL
from aura.observability.events import traced, emit, span
import asyncio, time
from aura.core import ServiceError
from .ranking import sparse

@traced('retrieval')
async def search(pipeline,question,k=4,document_id=None):
    """Purpose: Hybrid retrieval.
    
    Inputs: Pipeline, question, k and optional document ID.
    Process and rationale: Read scoped corpus, embed query, retrieve dense and BM25 candidates, fuse reciprocal ranks, deduplicate and try hosted reranking.
    Returns: Chunks with reranking success/error and timing metadata.
    """
    if not question.strip() or len(question)>2000 or not 1<=k<=5: raise ServiceError('invalid_search')
    if document_id: pipeline.document(document_id)
    if document_id not in pipeline.corpus_cache:
        pipeline.corpus_cache[document_id]=await asyncio.to_thread(pipeline.store.all,document_id)
    corpus=pipeline.corpus_cache[document_id]
    documents={chunk.document_id for chunk in corpus}
    pages=[]
    for identifier in documents:
        pages.extend(pipeline.document(identifier).pages)
    emit('document_preparation', 'info', source='saved_index', documents=len(documents),
         pages=len(pages), chunks=len(corpus), ocr_pages=sum(page.ocr_applied for page in pages),
         unresolved_pages=sum(page.requires_ocr for page in pages))
    if not corpus: return {'chunks':[],'reranked':False,'rerank_error':None}
    vector=(await pipeline.embedding.embed([question]))[0]
    with span('dense_search'):
        dense=await asyncio.to_thread(pipeline.store.search,vector,10,document_id)
    with span('lexical_search'):
        lexical=sparse(question,corpus)[:10]
    # CORE LOGIC: RRF adds reciprocal rank contributions, not incomparable raw scores.
    scores={}; by_id={c.id:c for c in dense+lexical}
    for ranking in (dense,lexical):
        for rank,c in enumerate(ranking): scores[c.id]=scores.get(c.id,0)+1/(60+rank+1)
    emit('bm25_fusion', 'completed', dense_candidates=len(dense), lexical_candidates=len(lexical), corpus_chunks=len(corpus))
    ids=sorted(scores,key=scores.get,reverse=True)[:10]; selected=[by_id[i] for i in ids]
    unique={}
    for c in selected: unique.setdefault(c.content_hash,c)
    selected=list(unique.values()); start=time.monotonic(); error=None; reranked=False
    try:
        if getattr(pipeline,'local_embedding',False): raise ServiceError('local_hybrid_ranking')
        results=await pipeline.gateway.rerank(question,[c.text for c in selected])
        indices=[r['id'] for r in sorted(results,key=lambda r:r['score'],reverse=True)]
        if len(set(indices))!=len(indices) or any(not isinstance(i,int) or not 0<=i<len(selected) for i in indices): raise ServiceError('invalid_rerank_response')
        if not indices: raise ServiceError('empty_rerank_response')
        selected=[selected[i] for i in indices]; reranked=True
    except ServiceError as e:
        error=e.code
        emit('rerank_fallback', 'info', error=e.code)
    return {'chunks':selected[:k],'reranked':reranked,'rerank_error':error,'rerank_seconds':time.monotonic()-start}
