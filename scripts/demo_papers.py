"""Four-paper AURA demo with a live, auditable workflow trace."""
import argparse
import asyncio
import json
from pathlib import Path
import httpx

from aura.agents.contracts import Budget, GoalInput, Plan, Task
from aura.orchestration.workflow.engine import Engine
from aura.orchestration.workflow.persistence import Memory
from aura.agents.tools.dispatcher import Dispatcher
from aura.core import Settings, configure_logging
from aura.llm.gateway import Gateway
from aura.nlp.service import NLP
from aura.rag.pipeline import Pipeline
from aura.llm.transport import Transport

PAPERS = [
    ('attention-is-all-you-need.pdf', 'Transformer', 'What architecture and training advantages does the Transformer paper claim?'),
    ('retrieval-augmented-generation.pdf', 'RAG', 'How does RAG combine parametric and non-parametric memory?'),
    ('react.pdf', 'ReAct', 'How does ReAct combine reasoning traces with actions?'),
    ('self-rag.pdf', 'Self-RAG', 'How does Self-RAG decide when to retrieve and critique evidence?'),
]
ARXIV = {
    'attention-is-all-you-need.pdf': '1706.03762',
    'retrieval-augmented-generation.pdf': '2005.11401',
    'react.pdf': '2210.03629',
    'self-rag.pdf': '2310.11511',
}


async def download_paper(path, filename):
    paper = path / 'papers' / filename
    if paper.exists():
        return paper
    paper.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        response = await client.get(f'https://arxiv.org/pdf/{ARXIV[filename]}')
        response.raise_for_status()
    if not response.content.startswith(b'%PDF') or len(response.content) > 5 * 1024 * 1024:
        raise RuntimeError(f'Invalid or oversized PDF: {filename}')
    paper.write_bytes(response.content)
    return paper


async def watch(memory, workflow_id, project_id, run):
    after = 0
    while True:
        for event in memory.events(workflow_id, project_id, after):
            after = event['sequence']
            details = ' '.join(f'{k}={event[k]}' for k in ('task_id', 'agent_id', 'tool', 'provider', 'model', 'tokens', 'error', 'outcome') if k in event)
            print(f"[{after:03d}] {event['state']:<10} {event['type']:<18} {details}", flush=True)
        if run.done():
            break
        await asyncio.sleep(0.25)


def make_plan(documents):
    tasks = []
    for index, (filename, title, question) in enumerate(PAPERS, 1):
        tasks.append(Task(
            id=f'research_{index}', agent='research',
            description=f'Research {title} in document_id {documents[filename]}. Find a short exact quote and summarize its central method and contribution. Search question: {question}',
            tools=['rag_search'], acceptance=['One exact cited quote and a short method summary.'],
            max_steps=3, max_retries=2,
        ))
    tasks.append(Task(
        id='synthesis', agent='analysis', dependencies=[t.id for t in tasks],
        description='Compare the four papers: Transformer foundation, RAG retrieval, ReAct tool use, and Self-RAG adaptive retrieval. Identify concrete implications for AURA and limitations. Use only prior cited evidence.',
        tools=[], acceptance=['A comparative synthesis grounded in the four research outputs.'],
        max_steps=2, max_retries=1,
    ))
    tasks.append(Task(
        id='report', agent='reporting', dependencies=[t.id for t in tasks],
        description='Assemble the cited research report.', tools=[],
        acceptance=['A report with source evidence.'], max_steps=1, max_retries=0,
    ))
    return Plan(tasks=tasks)


async def main(mode):
    configure_logging()
    settings = Settings()
    if settings.aura_llm_provider != 'agentrouter':
        raise RuntimeError('Set AURA_LLM_PROVIDER=agentrouter in .env for this demo.')
    transport = Transport(settings)
    gateway = Gateway(settings, transport)
    path = Path(settings.data_dir)
    rag = Pipeline(gateway, path, settings.qdrant_url)
    memory = Memory(path / 'workflows.sqlite')
    try:
        documents = {d.filename: d.id for d in rag.documents()}
        if mode in ('all', 'ingest'):
            for filename, title, _ in PAPERS:
                if filename not in documents:
                    print(f'INGEST {title}: extracting, embedding, and indexing...', flush=True)
                    paper = await download_paper(path, filename)
                    result = await rag.ingest(filename, paper.read_bytes())
                    documents[filename] = result['document'].id
                    print(f"INGESTED {title}: {result['chunks']} chunks", flush=True)
                else:
                    print(f'REUSED {title}: indexed document', flush=True)
        if mode == 'ingest':
            return
        missing = [name for name, _, _ in PAPERS if name not in documents]
        if missing:
            raise RuntimeError(f'Index the papers first: {missing}')
        if mode in ('all', 'query'):
            print('TEST 1: cited question on the RAG paper', flush=True)
            answer = await rag.query('What two kinds of memory does the RAG paper combine?', documents['retrieval-augmented-generation.pdf'])
            print(json.dumps({'answer': answer['answer'].model_dump(), 'usage': answer.get('usage'), 'reranked': answer['retrieval']['reranked']}, indent=2), flush=True)
            Path('reports/paper-query.json').write_text(json.dumps({'answer': answer['answer'].model_dump(), 'usage': answer.get('usage'), 'reranked': answer['retrieval']['reranked']}, indent=2))
        if mode == 'query':
            return
        plan = make_plan(documents)
        goal = GoalInput(
            project_id='aura_papers',
            goal='Generate a comparative report on four research papers, with exact citations, explaining their methods and what they imply for the AURA student project.',
            document_ids=[documents[name] for name, _, _ in PAPERS],
            acceptance=['Evidence references and exact quotes are valid.'],
            budget=Budget(llm_calls=24, tool_calls=16, seconds=600, concurrency=2),
        )
        goal_id = memory.create_goal(goal)
        workflow_id = memory.create(goal_id, goal.project_id, plan.model_dump())
        engine = Engine(gateway, memory, Dispatcher(rag, NLP(rag.embedding), path / 'files', memory))
        print(f'TEST 2: agent workflow {workflow_id}', flush=True)
        for task in plan.tasks:
            print(f'PLAN {task.id}: {task.agent}; depends on {task.dependencies}; tools {task.tools}', flush=True)
        run = asyncio.create_task(engine.execute(workflow_id, goal.project_id))
        await watch(memory, workflow_id, goal.project_id, run)
        result = await run
        print(f"FINAL state={result['state']} error={result['error']} llm_calls={result['llm_calls']} tool_calls={result['tool_calls']}", flush=True)
        events = memory.events(workflow_id, goal.project_id)
        Path('reports/papers-workflow.json').write_text(json.dumps({'workflow': result, 'events': events}, indent=2))
        trace = [f'Workflow {workflow_id}', *[f"[{e['sequence']:03d}] {e['state']:<10} {e['type']:<18} " + ' '.join(f'{k}={v}' for k, v in e.items() if k not in ('sequence', 'time', 'state', 'type')) for e in events], f"FINAL state={result['state']} error={result['error']}"]
        Path('reports/papers-workflow.log').write_text('\n'.join(trace) + '\n')
        lines = ['# AURA four-paper agent report', '', f"Workflow: `{workflow_id}`; state: **{result['state']}**", '']
        for filename, title, _ in PAPERS:
            index = [name for name, _, _ in PAPERS].index(filename) + 1
            output = result['tasks'].get(f'research_{index}', {}).get('output', {})
            lines.extend([f'## {title}', '', output.get('summary', 'No research output.'), ''])
            for evidence in output.get('evidence', []):
                lines.append(f"- Source quote: “{evidence['quote']}” ([paper](https://arxiv.org/abs/{ARXIV[filename]}), chunk `{evidence['chunk_id']}`)")
            lines.append('')
        synthesis = result['tasks'].get('synthesis', {}).get('output', {})
        lines.extend(['## Comparative synthesis', '', synthesis.get('summary', 'No synthesis output.'), '', '## Verification', '', json.dumps((result.get('report') or {}).get('verification', {}), indent=2), ''])
        Path('reports/papers-report.md').write_text('\n'.join(lines))
    finally:
        memory.close()
        rag.close()
        await transport.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('all', 'ingest', 'query', 'workflow'), default='all')
    args = parser.parse_args()
    asyncio.run(main(args.mode))
