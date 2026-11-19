"""
FILE: backend/src/aura/agents/context.py
PURPOSE: Build a bounded prompt view without altering stored observations.
MAIN RESPONSIBILITY: Agent Context Budget.
INPUTS: Goal, task, prior outputs, observations, failures, tool catalog and feedback.
OUTPUTS: JSON prompt within the character budget.
IMPORTANT FUNCTIONS / CLASSES: build_context.
CONNECTED MODULES: aura.core.
WHERE THIS FILE IS USED: backend/src/aura/agents/worker.py.
PRESENTATION EXPLANATION: "We shorten the prompt view while retaining complete tool observations in memory."
"""
# PRESENTATION SECTION: AGENT CONTEXT BUDGET
import copy
import json
from aura.core import ServiceError


def build_context(goal, task, prior, observations, failures, catalog, feedback):
    """Purpose: Context management.
    
    Inputs: Goal, task, prior outputs, observations, failures, tools and feedback.
    Process and rationale: Copy and deduplicate observations, shorten prompt-visible passages and retain required-tool tracking without altering full stored evidence.
    Returns: Bounded JSON prompt or context-budget error.
    """
    payload={'goal':goal.goal,'task':task.model_dump(), 'prior_results':copy.deepcopy(prior),
             'observations':copy.deepcopy(observations),'previous_failures':failures[-2:],
             'tools':catalog,'feedback':feedback,
             'required_tools_remaining':sorted(set(task.tools)-{o['tool'] for o in observations})}
    # Drop duplicate retrieved chunks; keep their original IDs and literal prefixes.
    seen=set()
    for observation in reversed(payload['observations']):
        data=observation['data']
        if observation['tool']=='rag_search':
            unique=[]
            for chunk in data['chunks']:
                if chunk['id'] not in seen:
                    seen.add(chunk['id']);unique.append({k:chunk[k] for k in ('id','document_id','text')})
            data['chunks']=unique
    for limit in (1000,600,300,120):
        view=copy.deepcopy(payload)
        for output in view['prior_results']:
            output['summary']=output['summary'][:limit]
            output['evidence']=output.get('evidence',[])[:6]
            for evidence in output['evidence']:evidence['quote']=evidence['quote'][:120]
        for observation in view['observations']:
            data=observation['data']
            if observation['tool']=='rag_search':
                for chunk in data['chunks']:chunk['text']=chunk['text'][:limit]
            elif observation['tool']=='document_read':
                for page in data['pages']:page['text']=page['text'][:limit]
            elif observation['tool']=='file_read':data['text']=data['text'][:limit]
            elif observation['tool']=='nlp_analyze':
                for key in ('tokens','entities','sentences'):
                    if key in data:data[key]=data[key][:10]
        text=json.dumps(view,ensure_ascii=False,separators=(',',':'))
        if len(text)<=11000:return text
    raise ServiceError('context_budget_exhausted')
