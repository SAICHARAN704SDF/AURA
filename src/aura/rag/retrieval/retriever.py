"""Dense/BM25 fusion, deduplication, and provider reranking."""
from aura.observability.events import traced, emit, span
import asyncio, time
from aura.core import ServiceError
from .ranking import sparse

@traced('retrieval')
async def search(pipeline,question,k=4,document_id=None):
    if not question.strip() or len(question)>2000 or not 1<=k<=5: raise ServiceError('invalid_search')
    if document_id: pipeline.document(document_id)
    if document_id not in pipeline.corpus_cache:
        pipeline.corpus_cache[document_id]=await asyncio.to_thread(pipeline.store.all,document_id)
    corpus=pipeline.corpus_cache[document_id]
    if not corpus: return {'chunks':[],'reranked':False,'rerank_error':None}
    vector=(await pipeline.embedding.embed([question]))[0]
    with span('dense_search'):
        dense=await asyncio.to_thread(pipeline.store.search,vector,10,document_id)
    lexical=sparse(question,corpus)[:10]; scores={}; by_id={c.id:c for c in dense+lexical}
    for ranking in (dense,lexical):
        for rank,c in enumerate(ranking): scores[c.id]=scores.get(c.id,0)+1/(60+rank+1)
    emit('bm25_fusion', 'completed', dense_candidates=len(dense), lexical_candidates=len(lexical), corpus_chunks=len(corpus))
    ids=sorted(scores,key=scores.get,reverse=True)[:10]; selected=[by_id[i] for i in ids]
    unique={}
    for c in selected: unique.setdefault(c.content_hash,c)
    selected=list(unique.values()); start=time.monotonic(); error=None; reranked=False
    try:
        results=await pipeline.gateway.rerank(question,[c.text for c in selected])
        indices=[r['id'] for r in sorted(results,key=lambda r:r['score'],reverse=True)]
        if len(set(indices))!=len(indices) or any(not isinstance(i,int) or not 0<=i<len(selected) for i in indices): raise ServiceError('invalid_rerank_response')
        if not indices: raise ServiceError('empty_rerank_response')
        selected=[selected[i] for i in indices]; reranked=True
    except ServiceError as e:
        error=e.code
        emit('rerank_fallback', 'info', error=e.code)
    return {'chunks':selected[:k],'reranked':reranked,'rerank_error':error,'rerank_seconds':time.monotonic()-start}
