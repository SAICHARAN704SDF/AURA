"""Local evidence annotations for research text. All offsets index the original input."""
from collections import Counter
import re

from spacy.matcher import PhraseMatcher
from spacy.tokens import Span
from spacy.util import filter_spans

DEFAULT_TERMS = {
    "PAPER": ["this paper", "this study", "the paper", "the study"],
    "MODEL": ["BERT", "RoBERTa", "T5", "GPT-2", "GPT-3", "GPT-4", "ResNet"],
    "DATASET": ["SQuAD", "GLUE", "ImageNet", "MNIST", "CIFAR-10", "CoNLL-2003"],
    "METHOD": ["retrieval-augmented generation", "fine-tuning", "contrastive learning",
               "self-attention", "gradient descent"],
}
PREDICATES = {
    "wrote": "wrote", "authored": "wrote", "co-authored": "wrote",
    "is affiliated with": "affiliated_with", "was affiliated with": "affiliated_with",
    "uses": "uses", "used": "uses", "employs": "uses",
    "was evaluated on": "evaluated_on", "is evaluated on": "evaluated_on",
    "was tested on": "evaluated_on", "is trained on": "trained_on", "was trained on": "trained_on",
}


def build_matcher(engine, terms):
    """Compile configured domain vocabulary once, using case-insensitive token matches."""
    matcher = PhraseMatcher(engine.vocab, attr="LOWER")
    for label, values in terms.items():
        matcher.add(label, [engine.make_doc(value) for value in values])
    return matcher


def annotate(doc, matcher):
    """Extract conservative sentence-local triples and explicit short-form references."""
    domain = [Span(doc, start, end, label=label) for label, start, end in matcher(doc)]
    # Prefer a domain term over overlapping, less specific trained English labels.
    covered = {i for span in domain for i in range(span.start, span.end)}
    entities = sorted(filter_spans(domain + [span for span in doc.ents
                      if not any(i in covered for i in range(span.start, span.end))]), key=lambda s: s.start)
    def record(span):
        return {"text": span.text, "label": span.label_, "start": span.start_char, "end": span.end_char}

    relations, references = [], []
    previous = []
    for sentence in doc.sents:
        local = [span for span in entities if sentence.start <= span.start < sentence.end]
        # A direct affirmative clause is required. Sentence offsets let a reader verify each edge.
        if not re.search(r"\b(?:if|whether|might|possibly|not|never|hypothesiz\w*)\b", sentence.text, re.I):
            for left, right in zip(local, local[1:]):
                predicate = PREDICATES.get(" ".join(doc[left.end:right.start].text.lower().split()))
                if predicate:
                    relations.append({"subject": record(left), "predicate": predicate, "object": record(right),
                                      "evidence": sentence.text, "start": sentence.start_char, "end": sentence.end_char})
        # Restrict linking to typed mentions in the next sentence. Ambiguity causes abstention.
        for match in re.finditer(r"\b(?:this|the) (model|dataset|method|organization|researcher)\b", sentence.text, re.I):
            label = {"organization": "ORG", "researcher": "PERSON"}.get(match[1].lower(), match[1].upper())
            candidates = [item for item in previous if item.label_ == label]
            if len(candidates) == 1 and not any(item.end_char <= sentence.start_char + match.start() for item in local):
                references.append({"mention": match[0], "start": sentence.start_char + match.start(),
                                   "end": sentence.start_char + match.end(), "antecedent": record(candidates[0])})
        previous = local
    return [record(span) for span in entities], relations, references


def extractive_summary(doc, limit=3):
    """Score sentences by content-term frequency, then restore source order and offsets."""
    sentences = list(doc.sents)
    terms = [[(token.lemma_ or token.text).casefold() for token in sent
              if token.is_alpha and not token.is_stop] for sent in sentences]
    frequencies = Counter(word for words in terms for word in words)
    def score(index):
        words = terms[index]
        return sum(frequencies[word] for word in set(words)) / max(1, len(words)) ** 0.5
    selected = sorted(sorted(range(len(sentences)), key=score, reverse=True)[:limit])
    evidence = [{"text": sentences[i].text, "start": sentences[i].start_char,
                 "end": sentences[i].end_char} for i in selected]
    return {"method": "extractive_term_frequency", "text": " ".join(row["text"] for row in evidence),
            "evidence": evidence}


def detect_language(doc):
    """Estimate English, Spanish, French or German using stopword coverage; abstain on weak evidence."""
    from spacy.lang.de.stop_words import STOP_WORDS as de
    from spacy.lang.en.stop_words import STOP_WORDS as en
    from spacy.lang.es.stop_words import STOP_WORDS as es
    from spacy.lang.fr.stop_words import STOP_WORDS as fr
    words = {token.lower_ for token in doc if token.is_alpha}
    scores = sorted(((len(words & lexicon), code) for code, lexicon in
                     [("en", en), ("de", de), ("fr", fr), ("es", es)]), reverse=True)
    best, second = scores[:2]
    code = best[1] if best[0] >= 2 and best[0] >= second[0] + 2 else "und"
    return {"code": code, "method": "stopword_overlap", "matched_terms": best[0]}
