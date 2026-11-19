"""Compare offline lexical retrieval, spaCy tok2vec pooling, and a sentence encoder.

The benchmark rebuilds each representation on the same corpus and ranks by cosine.
Its ephemeral indexes never touch the application's production vector store.
"""
import argparse
import json
from hashlib import sha256
from math import log2
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy

from aura.rag.retrieval.evaluation import retrieval_metrics


def benchmark_scores(scores, ids, questions, k):
    metrics = []
    rankings = []
    for similarities, question in zip(scores, questions, strict=True):
        ranked = [ids[i] for i in np.argsort(-similarities, kind="stable")]
        gold = set(question["relevant"])
        values = retrieval_metrics(ranked, gold, k)
        dcg = sum(1/log2(2+i) for i, doc in enumerate(ranked[:k]) if doc in gold)
        ideal = sum(1/log2(2+i) for i in range(min(len(gold), k)))
        values["ndcg_at_k"] = dcg / ideal
        metrics.append(values)
        rankings.append({"question":question["text"], "top_ids":ranked[:k]})
    return {"metrics":{key:mean(row[key] for row in metrics) for key in metrics[0]},"rankings":rankings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("datasets/samples/retrieval_methods.json"))
    parser.add_argument("--sentence-model",default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--allow-download",action="store_true",help="Allow downloading public encoder weights")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    raw = args.dataset.read_bytes()
    dataset = json.loads(raw)
    ids, passages = list(dataset["passages"]), list(dataset["passages"].values())
    questions = dataset["questions"]
    if not 1 <= args.top_k <= len(ids) or not questions or any(
        not q["relevant"] or set(q["relevant"])-set(ids) for q in questions):
        parser.error("invalid k or missing gold document IDs")
    queries = [row["text"] for row in questions]
    report = {"dataset_sha256":sha256(raw).hexdigest(), "passages":len(ids), "questions":len(queries),
              "top_k":args.top_k, "timing":"model load, corpus/query encoding and similarity, CPU seconds",
              "systems":{}}
    for name in ("tfidf", "en_core_web_sm_tok2vec_mean", args.sentence_model):
        start = perf_counter()
        if name == "tfidf":
            encoder = TfidfVectorizer(ngram_range=(1,2))
            docs = encoder.fit_transform(passages)
            vectors = encoder.transform(queries)
        elif name == "en_core_web_sm_tok2vec_mean":
            encoder = spacy.load("en_core_web_sm", enable=["tok2vec"])
            encoded = np.asarray([d.tensor.mean(axis=0) for d in encoder.pipe(passages+queries)])
            docs, vectors = encoded[:len(ids)], encoded[len(ids):]
        else:
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(name, device="cpu", local_files_only=not args.allow_download)
            encoded = encoder.encode(passages+queries, show_progress_bar=False)
            docs, vectors = encoded[:len(ids)], encoded[len(ids):]
        scores = cosine_similarity(vectors, docs)
        elapsed = perf_counter() - start
        report["systems"][name] = {**benchmark_scores(scores, ids, questions, args.top_k),
                                   "seconds":round(elapsed,4), "dimensions":docs.shape[1]}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
