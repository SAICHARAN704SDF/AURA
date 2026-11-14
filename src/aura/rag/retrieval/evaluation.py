"""Deterministic retrieval and citation metrics; no simulated faithfulness score."""
def retrieval_metrics(retrieved: list[str], relevant: set[str], k: int=5) -> dict:
    if k<1: raise ValueError('k must be positive')
    ranked=list(dict.fromkeys(retrieved))[:k]
    hits=sum(x in relevant for x in ranked)
    reciprocal=next((1/(i+1) for i,x in enumerate(ranked) if x in relevant),0.0)
    return {'precision_at_k':hits/k,'recall_at_k':hits/len(relevant) if relevant else 0.0,'mrr':reciprocal}
