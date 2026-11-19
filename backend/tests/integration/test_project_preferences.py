import io
import socket
import sqlite3
from types import SimpleNamespace
import zipfile
import pytest
from fastapi.testclient import TestClient
from aura.api import create_app
from aura.core import Settings, ServiceError
from aura.memory.profiles import Profiles, Feedback, Profile
from aura.rag.ingestion.documents import load
from aura.rag.ingestion.public_web import target

def test_profiles_are_isolated_durable_and_bounded(tmp_path):
    path=tmp_path/'meta.db'
    db=sqlite3.connect(path)
    profiles=Profiles(db)
    profiles.save('one',Profile(preferences='Short paragraphs',adaptive_retrieval=True))
    for doc,vote in [('a',-1),('b',1),('c',1)]:
        profiles.vote('one',Feedback(document_id=doc,section='Results',vote=vote))
    db.close()
    db=sqlite3.connect(path)
    p=Profiles(db)
    assert p.get('one').preferences=='Short paragraphs'
    candidates=[SimpleNamespace(document_id=d) for d in 'abc']
    assert p.rank('one',candidates)==[candidates[1],candidates[0],candidates[2]]
    assert p.rank('other',candidates)==candidates and not p.get('other').adaptive_retrieval
    db.close()


def test_profile_route_and_goal_snapshot(tmp_path):
    with TestClient(create_app(Settings(_env_file=None,data_dir=str(tmp_path)))) as c:
        assert c.put('/projects/one/profile',json={'preferences':'Use bullets'}).status_code==200
        assert c.get('/projects/two/profile').json()['preferences']==''
        goal=c.post('/goals',json={'project_id':'one','goal':'Explain'}).json()['id']
        assert c.get(f'/goals/{goal}?project_id=one').json()['presentation_preferences']=='Use bullets'
        assert c.put('/projects/one/feedback',json={'section':'methods','document_id':'missing','vote':1}).status_code==404


def test_docx_and_html_metadata():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as file:
        file.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:t>Study overview.</w:t></w:p></w:document>')
    assert load('study.docx',buffer.getvalue()).pages[0].text=='Study overview.'
    page=load('paper.html',b'<head><title>Research</title><meta name="citation_author" content="A. Lee"/></head><nav>Skip menus</nav><article>Evidence.</article>')
    assert page.metadata=={'title':'Research','author':'A. Lee'}
    assert page.pages[0].text=='Evidence.'


def test_public_source_address_validation(monkeypatch):
    def lookup(*args,**kwargs):
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
    monkeypatch.setattr(socket,'getaddrinfo',lookup)
    with pytest.raises(ServiceError,match='invalid_public_url'):
        target('https://paper.example/test')
