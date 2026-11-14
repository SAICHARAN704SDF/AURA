"""Token, sentence, POS, lemma, dependency, and entity extraction."""
from aura.core import ServiceError
from aura.observability.events import emit, span


class LinguisticProcessor:
    def __init__(self):
        self.engine = None
        self.trained = False

    def initialize(self):
        if self.engine is None:
            import spacy
            try:
                self.engine = spacy.load('en_core_web_sm')
                self.trained = True
            except OSError:
                self.engine = spacy.blank('en')
                self.engine.add_pipe('sentencizer')

    def status(self):
        return {
            'loaded': self.engine is not None,
            'trained_pipeline': self.trained,
            'classification': 'unavailable_no_verified_task_checkpoint',
            'relations': 'unavailable',
            'ocr': 'unavailable',
        }

    def analyze(self, text):
        if not text.strip() or len(text) > 20000:
            raise ServiceError('invalid_nlp_input')
        self.initialize()
        with span('spacy_pipeline'):
            doc = self.engine(text)
        emit('nlp_annotations', 'completed', tokens=len(doc), sentences=sum(1 for _ in doc.sents), entities=len(doc.ents), trained_pipeline=self.trained, annotations=['tokens','sentences','pos','lemmas','dependencies','entities'] if self.trained else ['tokens','sentences'])
        return {
            'tokens': [{'text': t.text, 'start': t.idx, 'pos': t.pos_ or None,
                        'lemma': t.lemma_ or None, 'dependency': t.dep_ or None} for t in doc],
            'sentences': [sentence.text for sentence in doc.sents],
            'entities': [{'text': entity.text, 'label': entity.label_,
                          'start': entity.start_char, 'end': entity.end_char} for entity in doc.ents],
            'status': self.status(),
        }
