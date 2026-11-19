"""
FILE: backend/src/aura/agents/tools/dispatcher.py
PURPOSE: Validate, scope and execute only tools allowed for the task and role.
MAIN RESPONSIBILITY: Permission-Checked Tools.
INPUTS: Workflow, task, goal, tool name, arguments and call ID.
OUTPUTS: Audited ToolResult cached by call ID.
IMPORTANT FUNCTIONS / CLASSES: SearchArgs, DocumentArgs, NLPArgs, CalculatorArgs, FileArgs, ToolResult, Dispatcher.
CONNECTED MODULES: aura.core, aura.agents.contracts.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py, backend/src/aura/agents/verification/checks.py.
PRESENTATION EXPLANATION: "Model output requests an action; this dispatcher decides whether it may execute."
"""
# PRESENTATION SECTION: PERMISSION-CHECKED TOOLS
import asyncio, inspect, math, operator
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
class ProgramArgs(Strict):
    program:str=Field(min_length=1,max_length=1000)
class PublicationArgs(Strict):
    query:str=Field(min_length=1,max_length=300)
class ToolResult(Strict):
    call_id:str
    tool:str
    data:dict
SCHEMAS={'numeric_program':ProgramArgs,'publication_search':PublicationArgs,'rag_search':SearchArgs,'document_read':DocumentArgs,'nlp_analyze':NLPArgs,'calculator':CalculatorArgs,'file_read':FileArgs}
OPS={'+':operator.add,'-':operator.sub,'*':operator.mul,'/':operator.truediv,'>=':operator.ge,'<=':operator.le,'>':operator.gt,'<':operator.lt,'==':operator.eq}
class Dispatcher:
    """Permission boundary between requested agent actions and executable tools. Uses RAG, NLP, scoped files and Memory to return audited, bounded ToolResults."""
    def __init__(self,rag,nlp,files:Path,memory):self.rag=rag;self.nlp=nlp;self.files=files;self.memory=memory
    def catalog(self):return [{'name':k,'arguments':v.model_json_schema(),'read_only':True,'timeout':30} for k,v in SCHEMAS.items()]
    async def call(self,w,task,goal,name,args,call_id):
        """Purpose: Tool permissions.
        
        Inputs: Workflow, task, goal, tool name, arguments and unique call ID.
        Process and rationale: Validate task/role permissions, schema, scope and budget; execute a bounded read-only tool and save its audited result.
        Returns: ToolResult, or cached result for the same call ID.
        """
        # CORE LOGIC: Both the task and the registered role must permit this action.
        if name not in task.tools or name not in AGENTS[task.agent].tools:raise ServiceError('tool_permission_denied')
        if name=='publication_search' and not goal.allow_public_search:raise ServiceError('public_search_disabled')
        model=SCHEMAS[name].model_validate(args)
        cached=self.memory.recall(w,'episodic',call_id)
        if cached:return ToolResult.model_validate(cached)
        if w['tool_calls']>=goal.budget.tool_calls:raise ServiceError('tool_budget_exhausted')
        w['tool_calls']+=1;self.memory.save(w,{'type':'tool_started','task_id':task.id,'tool':name,'call_id':call_id})
        async def execute():
            if name=='numeric_program':
                from .research import evaluate_program
                return evaluate_program(model.program)
            if name=='publication_search':
                from .research import search_publications
                return await search_publications(model.query)
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
                    scope={"project_id":goal.project_id} if "project_id" in inspect.signature(self.rag.search).parameters else {}
                    r=await self.rag.search(model.question,3,id,**scope)
                    results.append(r['chunks'])
                # Collect the first result from each source before considering second-best passages.
                from itertools import zip_longest
                balanced = [chunk.model_dump() for wave in zip_longest(*results)
                            for chunk in wave if chunk is not None]
                return {'chunks':balanced[:max(5,len(results))]}
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
