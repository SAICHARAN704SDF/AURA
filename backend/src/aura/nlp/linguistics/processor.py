"""
FILE: backend/src/aura/nlp/linguistics/processor.py
PURPOSE: Run the English spaCy pipeline with an explicit limited fallback.
MAIN RESPONSIBILITY: Linguistic Analysis.
INPUTS: Non-empty text up to 20000 characters.
OUTPUTS: Tokens, sentences, entities and capability status.
IMPORTANT FUNCTIONS / CLASSES: LinguisticProcessor.
CONNECTED MODULES: aura.core, aura.observability.events.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "The trained model adds POS, lemmas and dependencies; fallback only provides tokens and sentences."
"""
# PRESENTATION SECTION: LINGUISTIC ANALYSIS
from collections import Counter
import unicodedata
from threading import Lock
from .research import DEFAULT_TERMS, annotate, build_matcher, detect_language, extractive_summary
from aura.core import ServiceError
from aura.observability.events import emit, span


class LinguisticProcessor:
    """Lazy English spaCy processor. analyze returns annotations; status distinguishes a trained pipeline from basic token/sentence fallback."""
    def __init__(self, model="en_core_web_sm", terms=None):
        self.engine = None
        self.trained = False
        self.model = model
        self.terms = DEFAULT_TERMS if terms is None else {**DEFAULT_TERMS, **terms}
        self._load_lock = Lock()

    def initialize(self):
        """Publish a fully configured pipeline atomically to concurrent analysis requests."""
        if self.engine is not None:
            return
        with self._load_lock:
            if self.engine is not None:
                return
            import spacy
            try:
                engine = spacy.load(self.model)
            except OSError:
                if self.model != "en_core_web_sm":
                    raise ServiceError("configured_nlp_model_unavailable") from None
                engine = spacy.blank("en")
            if not any(engine.has_pipe(name) for name in ("parser", "senter", "sentencizer")):
                engine.add_pipe("sentencizer")
            self.matcher = build_matcher(engine, self.terms)
            self.trained = engine.has_pipe("ner")
            self.engine = engine

    def status(self):
        return {
            'loaded': self.engine is not None,
            'trained_pipeline': self.trained,
            'classification': 'unavailable_no_verified_task_checkpoint',
            'relations': 'affirmative_sentence_patterns',
            'coreference': 'typed_mentions_in_adjacent_sentences',
            'ner_model': self.model if self.trained else None,
            'ocr': __import__('aura.rag.ingestion.ocr',fromlist=['status']).status(),
        }

    def analyze(self, text):
        """Purpose: Linguistic analysis.
        
        Inputs: Non-empty text, at most 20000 characters.
        Process and rationale: Initialize spaCy, run its pipeline and emit annotation counts; trained English model supplies richer annotations than fallback.
        Returns: Tokens with offsets/POS/lemmas/dependencies, sentences, entities and status.
        """
        if not text.strip() or len(text) > 20000:
            raise ServiceError('invalid_nlp_input')
        self.initialize()
        with span('spacy_pipeline'):
            doc = self.engine(text)
        # Build a separate search vocabulary so source offsets stay valid.
        with span('text_preprocessing'):
            terms = Counter(
                unicodedata.normalize('NFKC', token.lemma_ or token.text).casefold()
                for token in doc if token.is_alpha and not token.is_stop
            )
        emit('vocabulary_summary', 'completed', unique_terms=len(terms), retained_terms=terms.total())
        with span('relation_extraction'):
            entities, relations, references = annotate(doc, self.matcher)
        emit('nlp_annotations', 'completed', tokens=len(doc), sentences=sum(1 for _ in doc.sents),
             entities=len(entities), relations=len(relations), coreference_links=len(references),
             trained_pipeline=self.trained, annotations=['tokens', 'sentences', 'entities'] +
             (['pos', 'lemmas', 'dependencies'] if self.engine.has_pipe('parser') else []))
        with span('extractive_summary'):
            summary = extractive_summary(doc)
        return {
            'language': detect_language(doc),
            'relations': relations, 'coreference': references, 'extractive_summary': summary,
            'knowledge_graph': {'nodes': entities, 'edges': relations},
            'preprocessing': {'unique_terms': len(terms), 'top_terms': terms.most_common(20)},
            'tokens': [{'text': t.text, 'start': t.idx, 'pos': t.pos_ or None,
                        'lemma': t.lemma_ or None, 'dependency': t.dep_ or None} for t in doc],
            'sentences': [sentence.text for sentence in doc.sents],
            'entities': entities,
            'status': self.status(),
        }
