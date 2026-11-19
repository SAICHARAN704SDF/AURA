"""Research annotations preserve literal offsets and explicitly abstain on ambiguity."""
import asyncio
from types import SimpleNamespace

import pytest

from aura.nlp.api.routes import Summary, summarize
from aura.nlp.linguistics.processor import LinguisticProcessor
from aura.nlp.service import NLP


@pytest.fixture(scope="module")
def processor():
    return LinguisticProcessor(terms={"MODEL":["AtlasNet","BERT","T5"]})


def test_graph_evidence_and_coreference(processor):
    text = "AtlasNet was evaluated on SQuAD. This model predicts answer spans."
    analysis = processor.analyze(text)
    edge, = analysis["relations"]
    assert edge["subject"]["text"] == "AtlasNet" and edge["predicate"] == "evaluated_on"
    assert edge["object"]["label"] == "DATASET"
    assert text[edge["start"]:edge["end"]] == edge["evidence"]
    assert analysis["knowledge_graph"]["edges"] == [edge]
    link, = analysis["coreference"]
    assert text[link["start"]:link["end"]] == link["mention"] == "This model"
    assert link["antecedent"]["text"] == "AtlasNet"


def test_negation_ambiguity_and_language(processor):
    assert not processor.analyze("T5 was not tested on SQuAD.")["relations"]
    assert not processor.analyze("BERT and T5 were compared. This model is slow.")["coreference"]
    assert processor.analyze("MNIST.")["language"]["code"] == "und"
    assert processor.analyze("This is the text of the article and it describes our method.")["language"]["code"] == "en"


def test_summarization_modes(processor):
    calls = []
    class Gateway:
        def preferred_generation(self):
            return "test", "small"
        async def generate(self, provider, model, request, **kwargs):
            calls.append(request)
            return SimpleNamespace(text="The model predicts spans.", model=model, tokens=12)
    nlp = NLP(None)
    nlp.linguistics = processor
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(nlp=nlp,gateway=Gateway())))
    text = "AtlasNet predicts answer spans. The evaluation used SQuAD."
    extract = asyncio.run(summarize(Summary(text=text,sentences=1),request))
    assert len(extract["evidence"]) == 1 and extract["text"] in text and not calls
    abstract = asyncio.run(summarize(Summary(text=text,mode="abstractive",sentences=1),request))
    assert abstract["model"] == "small" and len(calls) == 1
    assert extract["text"] in calls[0].prompt
