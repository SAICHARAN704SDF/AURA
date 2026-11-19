"""Measure how much annotated evidence different chunk boundaries preserve in retrieval.

Pooled passage gold is expressed in source offsets. Score a retrieval hit only when
a retrieved chunk covers at least 80% of a labeled passage. Report the number of
characters retrieved alongside quality: large chunks can otherwise look artificially good.
"""
import argparse
import asyncio
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean

import numpy as np
from sentence_transformers import SentenceTransformer

from aura.rag.chunking.chunker import chunks
from aura.rag.ingestion.documents import load


def overlap_fraction(start, end, chunk):
    overlap = max(0, min(end, chunk.end) - max(start, chunk.start))
    return overlap / (end - start)


async def run(args):
    dataset = json.loads(args.dataset.read_bytes())
    corpus = ""
    for topic, text in dataset["passages"].items():
        corpus += f"\n\n# {topic.title()}\n"
        corpus += text
    document = load("methods.md", corpus.encode())
    # Match the exact offsets of the text emitted by the production loader.
    source = document.pages[0].text
    labels = {name: (source.index(text), source.index(text) + len(text)) for name,text in dataset["passages"].items()}
    encoder = SentenceTransformer(args.model, device="cpu", local_files_only=not args.allow_download)
    def encode(texts):
        return encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    queries = dataset["questions"]
    query_vectors = encode([row["text"] for row in queries])
    report = {"dataset_sha256": sha256(args.dataset.read_bytes()).hexdigest(), "model":args.model,
              "windowed_strategies":{"size":args.size,"overlap":args.overlap},
              "semantic":{"base_sentence_window":600,"max_merged_characters":1800,"overlap":0,"threshold":0.8}, "top_k":args.k,
              "queries":len(queries), "gold_minimum_covered_fraction":0.8, "strategies":{}}
    for strategy in ("fixed", "recursive", "sentence", "structure", "semantic"):
        if strategy == "semantic":
            from aura.rag.chunking.chunker import semantic_chunks
            async def embed(texts):
                return encode(texts).tolist()
            sections = await semantic_chunks(document, embed, threshold=0.8)
        else:
            sections = chunks(document, size=args.size, overlap=args.overlap, strategy=strategy)
        vectors = encode([section.text for section in sections])
        ranks = np.argsort(-(query_vectors @ vectors.T), axis=1, kind="stable")
        recalls, mrr, context = [], [], []
        for row, order in zip(queries, ranks, strict=True):
            retrieved = [sections[i] for i in order[:args.k]]
            matched = [set(name for name in row["relevant"] if overlap_fraction(*labels[name], chunk) >= .8)
                       for chunk in retrieved]
            recalls.append(len(set().union(*matched))/len(row["relevant"]))
            mrr.append(next((1/i for i, hits in enumerate(matched, 1) if hits), 0))
            context.append(sum(len(chunk.text) for chunk in retrieved))
        report["strategies"][strategy] = {"chunks":len(sections),"mean_recall_at_k":mean(recalls),
                                          "mrr_at_k":mean(mrr),"mean_context_characters":mean(context)}
    print(json.dumps(report,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("datasets/samples/retrieval_methods.json"))
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--size", type=int, default=250)
    parser.add_argument("--overlap", type=int, default=32)
    parser.add_argument("-k", type=int, default=2)
    args = parser.parse_args()
    if args.k < 1:
        parser.error("k must be positive")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
