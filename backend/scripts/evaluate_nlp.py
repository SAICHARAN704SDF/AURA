"""Fine-tune an installed English spaCy NER pipeline and evaluate on a disjoint split.

Each JSONL row supplies split, text and [start, end, label] annotations in character
offsets. Test rows may also include a reference summary and literal relation triples.
The saved registry entry includes the base model, seed, dataset digest, and metrics.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import re
from tempfile import TemporaryDirectory

import spacy
from spacy.training import Example
from spacy.util import fix_random_seed, minibatch

from aura.nlp.linguistics.research import DEFAULT_TERMS, annotate, build_matcher, extractive_summary


def scores(tp, predicted, gold):
    return {"precision": tp / predicted if predicted else 0, "recall": tp / gold if gold else 0,
            "f1": 2 * tp / (predicted + gold) if predicted + gold else 0,
            "tp": tp, "predicted": predicted, "gold": gold}


def rouge(prediction, reference):
    """Compute ROUGE-1/2 and longest-common-subsequence F1 with a shared word tokenizer."""
    a, b = [re.findall(r"\w+", text.casefold()) for text in (prediction, reference)]
    result = {}
    for n in (1, 2):
        aa, bb = [Counter(zip(*(tokens[i:] for i in range(n)))) for tokens in (a, b)]
        result[f"rouge{n}"] = scores(sum((aa & bb).values()), sum(aa.values()), sum(bb.values()))["f1"]
    prev = [0] * (len(b) + 1)
    for left in a:
        curr = [0]
        for j, right in enumerate(b, 1):
            curr.append(prev[j-1]+1 if left == right else max(prev[j], curr[-1]))
        prev = curr
    result["rougeL"] = scores(prev[-1], len(a), len(b))["f1"]
    return result


def evaluate(engine, rows):
    matcher = build_matcher(engine, DEFAULT_TERMS)
    ner = Counter()
    triples = Counter()
    summary = Counter()
    for row in rows:
        doc = engine(row["text"])
        predicted = {(e.start_char, e.end_char, e.label_) for e in doc.ents}
        gold = set(map(tuple, row["entities"]))
        ner.update({"tp": len(predicted & gold), "pred": len(predicted), "gold": len(gold)})
        if "relations" in row:
            _, relations, _ = annotate(doc, matcher)
            predicted = {(r["subject"]["text"],r["predicate"],r["object"]["text"]) for r in relations}
            gold = set(map(tuple, row["relations"]))
            triples.update({"tp": len(predicted & gold), "pred": len(predicted), "gold": len(gold), "n": 1})
        if "summary" in row:
            summary.update(rouge(extractive_summary(doc, 1)["text"], row["summary"]))
            summary["n"] += 1
    return {"ner_exact_span": scores(ner["tp"], ner["pred"], ner["gold"]),
            "relation_exact_triple": scores(triples["tp"],triples["pred"],triples["gold"]) if triples["n"] else None,
            "extractive_summary": {k:summary[k]/summary["n"] for k in ("rouge1","rouge2","rougeL")} if summary["n"] else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("datasets/samples/nlp_research.jsonl"))
    parser.add_argument("--output", type=Path, required=True, help="New checkpoint directory, never overwritten")
    parser.add_argument("--base", default="en_core_web_sm")
    parser.add_argument("--epochs", type=int, default=12)
    args = parser.parse_args()
    if args.output.exists() or args.epochs < 1:
        parser.error("use a new output directory and a positive epoch count")
    raw = args.dataset.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    train, test = [[row for row in rows if row["split"] == split] for split in ("train","test")]
    if not train or not test or {r["text"] for r in train} & {r["text"] for r in test}:
        parser.error("training and test splits must be nonempty and contain disjoint texts")
    engine = spacy.load(args.base)
    ner = engine.get_pipe("ner")
    for row in rows:
        doc = engine.make_doc(row["text"])
        previous = 0
        for start, end, label in sorted(row["entities"]):
            if start < previous or doc.char_span(start,end) is None or not label:
                parser.error("invalid, overlapping or non-token-aligned gold annotation")
            previous = end
    report = {"base":args.base,"base_version":engine.meta["version"],"seed":17,"epochs":args.epochs,
              "train_documents":len(train),"test_documents":len(test),"sha256":sha256(raw).hexdigest(),
              "off_the_shelf":evaluate(engine, test)}
    fix_random_seed(17)
    shuffle = random.Random(17)
    with engine.select_pipes(enable=[p for p in ("tok2vec","ner") if engine.has_pipe(p)]):
        for row in train:
            for _,_,label in row["entities"]:
                ner.add_label(label)
        optimizer = engine.resume_training()
        for _ in range(args.epochs):
            shuffle.shuffle(train)
            for batch in minibatch(train, size=4):
                examples = [Example.from_dict(engine.make_doc(r["text"]), {"entities":r["entities"]}) for r in batch]
                engine.update(examples,sgd=optimizer,drop=0.15)
    report["fine_tuned"] = evaluate(engine,test)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=args.output.parent) as temp:
        staging = Path(temp) / "entry"
        engine.to_disk(staging)
        (staging/"evaluation.json").write_text(json.dumps(report,indent=2)+"\n")
        staging.rename(args.output)
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
