import json
import logging
from aura.observability.events import emit, span

def test_only_allowed_fields_reach_structured_logs(monkeypatch,caplog):
    monkeypatch.setenv('RESEARCHOS_JSON_LOGS','1')
    monkeypatch.setenv('RESEARCHOS_OTEL','1')
    with caplog.at_level(logging.INFO,logger='researchos.events'):
        with span('retrieval'):
            emit('lookup',tokens=2, prompt='private input', key='never-log')
    records=[json.loads(r.message) for r in caplog.records if r.name=='researchos.events']
    assert len(records)==3
    assert records[1]['tokens']==2
    assert 'private input' not in str(records) and 'never-log' not in str(records)
