"""Read-only tools; no eval, shell, arbitrary Python or unrestricted paths."""
import asyncio, math, operator
from pathlib import Path
from typing import Literal
from pydantic import Field
from aura.core import ServiceError
from aura.agents.contracts import Strict,AGENTS
class SearchArgs(Strict):
    question:str=Field(min_length=1,max_length=1000)
    document_id:str | None=None
class DocumentArgs(Strict):
    document_id:str
class NLPArgs(Strict):
    text:str=Field(min_length=1,max_length=3000)
class CalculatorArgs(Strict):
    left:float=Field(allow_inf_nan=False)
    right:float=Field(allow_inf_nan=False)
    operation:Literal['+','-','*','/','>=','<=','>','<','==']
class FileArgs(Strict):
    name:str=Field(pattern=r'^[a-zA-Z0-9_-]+\.(txt|md|csv)$')
class ToolResult(Strict):
    call_id:str
    tool:str
    data:dict
SCHEMAS={'rag_search':SearchArgs,'document_read':DocumentArgs,'nlp_analyze':NLPArgs,'calculator':CalculatorArgs,'file_read':FileArgs}
OPS={'+':operator.add,'-':operator.sub,'*':operator.mul,'/':operator.truediv,'>=':operator.ge,'<=':operator.le,'>':operator.gt,'<':operator.lt,'==':operator.eq}
class Dispatcher:
    def __init__(self,rag,nlp,files:Path,memory):self.rag=rag;self.nlp=nlp;self.files=files;self.memory=memory
    def catalog(self):return [{'name':k,'arguments':v.model_json_schema(),'read_only':True,'timeout':30} for k,v in SCHEMAS.items()]
    async def call(self,w,task,goal,name,args,call_id):
        if name not in task.tools or name not in AGENTS[task.agent].tools:raise ServiceError('tool_permission_denied')
        model=SCHEMAS[name].model_validate(args)
        cached=self.memory.recall(w,'episodic',call_id)
        if cached:return ToolResult.model_validate(cached)
        if w['tool_calls']>=goal.budget.tool_calls:raise ServiceError('tool_budget_exhausted')
        w['tool_calls']+=1;self.memory.save(w,{'type':'tool_started','task_id':task.id,'tool':name,'call_id':call_id})
        async def execute():
            if name=='calculator':
                try:result=OPS[model.operation](model.left,model.right)
                except (ZeroDivisionError,OverflowError):raise ServiceError('invalid_calculation') from None
                if isinstance(result,float) and not math.isfinite(result):raise ServiceError('invalid_calculation')
                return {'left':model.left,'right':model.right,'operation':model.operation,'result':result}
            if name=='rag_search':
                if not goal.document_ids:raise ServiceError('document_scope_required')
                if model.document_id and model.document_id not in goal.document_ids:raise ServiceError('document_scope_denied')
                results=[]
                for id in ([model.document_id] if model.document_id else goal.document_ids):
                    r=await self.rag.search(model.question,3,id)
                    results.extend(c.model_dump() for c in r['chunks'])
                return {'chunks':results[:5]}
            if name=='document_read':
                if model.document_id not in goal.document_ids:raise ServiceError('document_scope_denied')
                doc=self.rag.document(model.document_id)
                return {'document_id':doc.id,'pages':[{'number':p.number,'text':p.text[:3000],'requires_ocr':p.requires_ocr} for p in doc.pages[:3]]}
            if name=='nlp_analyze':return await asyncio.to_thread(self.nlp.analyze,model.text)
            root=(self.files/w['project_id']).resolve();path=root/model.name
            if path.is_symlink() or not path.is_file() or path.resolve().parent!=root:raise ServiceError('file_access_denied')
            if path.stat().st_size>10000:raise ServiceError('file_size_limit')
            return {'text':path.read_text(encoding='utf-8')}
        result=ToolResult(call_id=call_id,tool=name,data=await asyncio.wait_for(execute(),30))
        self.memory.put(w,'episodic',call_id,result.model_dump())
        self.memory.save(w,{'type':'tool_completed','task_id':task.id,'tool':name,'call_id':call_id})
        return result
