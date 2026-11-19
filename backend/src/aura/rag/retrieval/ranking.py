"""
FILE: backend/src/aura/rag/retrieval/ranking.py
PURPOSE: Implement lexical BM25-style ranking and cosine similarity.
MAIN RESPONSIBILITY: Bm25 And Cosine.
INPUTS: Query/corpus text or two vectors.
OUTPUTS: Ranked chunks or a scalar similarity.
IMPORTANT FUNCTIONS / CLASSES: tokens, sparse, cosine.
CONNECTED MODULES: aura.core.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py, backend/src/aura/nlp/semantic/similarity.py.
PRESENTATION EXPLANATION: "Word ranking and vector similarity are separate signals; neither proves that a claim is true."
"""
# PRESENTATION SECTION: BM25 AND COSINE
import math, re
from collections import Counter
from aura.core import ServiceError

def tokens(text): return re.findall(r'\w+',text.lower())
def sparse(query, corpus):
    """Purpose: BM25 lexical ranking.
    
    Inputs: Query string and chunk corpus.
    Process and rationale: Score matching terms using frequency, inverse document frequency and length normalization; complement semantic retrieval with lexical evidence.
    Returns: Positive-scoring chunks ordered by descending lexical score.
    """
    counts=[Counter(tokens(c.text)) for c in corpus]; avg=sum(sum(c.values()) for c in counts)/max(1,len(counts))
    scores=[]
    for chunk, count in zip(corpus,counts):
        score=0
        for word in set(tokens(query)):
            df=sum(word in c for c in counts); tf=count[word]
            if tf: score+=math.log(1+(len(counts)-df+0.5)/(df+0.5))*tf*2.5/(tf+1.5*(0.25+0.75*sum(count.values())/max(avg,1)))
        if score: scores.append((score,chunk))
    return [c for _,c in sorted(scores,key=lambda x:x[0],reverse=True)]

def cosine(a,b):
    """Purpose: Vector similarity.
    
    Inputs: Two vectors of equal dimension.
    Process and rationale: Normalize their dot product; reject dimension mismatch and return zero for a zero denominator.
    Returns: Cosine similarity scalar, not a probability or truth score.
    """
    if len(a)!=len(b): raise ServiceError('embedding_dimension_mismatch')
    denominator=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/denominator if denominator else 0.0
