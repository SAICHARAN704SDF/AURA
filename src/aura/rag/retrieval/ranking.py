"""Sparse ranking and vector similarity."""
import math, re
from collections import Counter
from aura.core import ServiceError

def tokens(text): return re.findall(r'\w+',text.lower())
def sparse(query, corpus):
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
    if len(a)!=len(b): raise ServiceError('embedding_dimension_mismatch')
    denominator=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/denominator if denominator else 0.0
