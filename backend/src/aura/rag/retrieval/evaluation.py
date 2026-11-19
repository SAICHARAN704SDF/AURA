"""
FILE: backend/src/aura/rag/retrieval/evaluation.py
PURPOSE: Measure ranked retrieval against known relevant identifiers.
MAIN RESPONSIBILITY: Retrieval Metrics.
INPUTS: Retrieved IDs, relevant ID set and k.
OUTPUTS: Precision@k, recall@k and reciprocal rank.
IMPORTANT FUNCTIONS / CLASSES: retrieval_metrics.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "These metrics assess retrieval, not whether a generated answer is factually correct."
"""
# PRESENTATION SECTION: RETRIEVAL METRICS
def retrieval_metrics(retrieved: list[str], relevant: set[str], k: int=5) -> dict:
    """Purpose: Retrieval evaluation.
    
    Inputs: Ranked IDs, relevant ID set and positive k.
    Process and rationale: Deduplicate ranked IDs and calculate precision, recall and reciprocal rank against labels.
    Returns: Metric dictionary; no generated faithfulness score.
    """
    if k<1: raise ValueError('k must be positive')
    ranked=list(dict.fromkeys(retrieved))[:k]
    hits=sum(x in relevant for x in ranked)
    reciprocal=next((1/(i+1) for i,x in enumerate(ranked) if x in relevant),0.0)
    return {'precision_at_k':hits/k,'recall_at_k':hits/len(relevant) if relevant else 0.0,'mrr':reciprocal}
