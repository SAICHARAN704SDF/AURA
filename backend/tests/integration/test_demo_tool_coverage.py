"""Exercise remaining tool paths in isolated storage, without provider calls."""
import asyncio
from types import SimpleNamespace
import pytest
from aura.agents.contracts import GoalInput,Task
from aura.agents.tools.dispatcher import Dispatcher
from aura.memory.manager import Memory
from aura.core import ServiceError


def test_document_nlp_and_file_tools_are_scoped(tmp_path):
    async def check():
        memory=Memory(tmp_path/'workflow.sqlite')
        goal=GoalInput(project_id='demo',goal='Inspect tools',document_ids=['paper'])
        gid=memory.create_goal(goal);w=memory.get(memory.create(gid,'demo'),'demo')
        class Documents:
            def document(self,id):return SimpleNamespace(id=id,pages=[SimpleNamespace(number=1,text='Source text.',requires_ocr=False)])
        class Words:
            def analyze(self,text):return {'tokens':[{'text':text}]}
        dispatcher=Dispatcher(Documents(),Words(),tmp_path/'files',memory)
        research=Task(id='r',agent='research',description='Read source',tools=['document_read'],acceptance=['source'])
        result=await dispatcher.call(w,research,goal,'document_read',{'document_id':'paper'},'read')
        assert result.data['pages'][0]['text']=='Source text.'
        with pytest.raises(ServiceError,match='document_scope_denied'):
            await dispatcher.call(w,research,goal,'document_read',{'document_id':'other'},'bad-read')
        analysis=Task(id='a',agent='analysis',description='Analyze words',tools=['nlp_analyze'],acceptance=['words'])
        assert (await dispatcher.call(w,analysis,goal,'nlp_analyze',{'text':'AURA'},'nlp')).data['tokens']
        folder=tmp_path/'files'/'demo';folder.mkdir(parents=True);(folder/'note.txt').write_text('Only this project can read this note.')
        execution=Task(id='e',agent='execution',description='Read note',tools=['file_read'],acceptance=['note'])
        assert 'Only this project' in (await dispatcher.call(w,execution,goal,'file_read',{'name':'note.txt'},'file')).data['text']
        (folder/'link.txt').symlink_to(folder/'note.txt')
        with pytest.raises(ServiceError,match='file_access_denied'):
            await dispatcher.call(w,execution,goal,'file_read',{'name':'link.txt'},'link')
        memory.close()
    asyncio.run(check())
