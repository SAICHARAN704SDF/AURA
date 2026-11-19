"""Named research strategies executed by the same budgeted LangGraph engine."""
from aura.agents.contracts import Plan, Task


def strategy_plan(goal):
    """Build either a single observe/act loop or a reviewable research DAG."""
    acceptance = goal.acceptance
    if goal.strategy == "single_react":
        return Plan(tasks=[Task(id="research_answer", agent="research", description=goal.goal[:1000],
                                tools=["rag_search"], acceptance=acceptance, max_steps=5)])
    if goal.strategy != "collaborative":
        raise ValueError("Unknown named strategy")

    def task(identifier, role, description, dependencies=(), tools=()):
        return Task(id=identifier, agent=role, description=description, dependencies=list(dependencies),
                    tools=list(tools), acceptance=acceptance, max_retries=0)

    return Plan(tasks=[
        task("find", "research", "Find direct evidence answering: " + goal.goal[:900], tools=["rag_search"]),
        task("challenge", "research", "Find counterexamples, uncertainty or conflicting evidence for: " + goal.goal[:850], tools=["rag_search"]),
        task("critique", "critic", "Identify unsupported inferences, scope mismatches and contradictory evidence. Cite both sides of unresolved disagreements.", ["find", "challenge"]),
        task("write", "writer", "Write a concise answer from the reviewed evidence. Attribute disagreements to sources and disclose unresolved issues.", ["find", "challenge", "critique"]),
    ])
