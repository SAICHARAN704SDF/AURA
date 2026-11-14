"""Primary LangGraph execution topology; task retries remain in the engine."""
from langgraph.graph import END, START, StateGraph
from .state import GraphState
from .nodes import prepare, wave, finalize


def build_graph(engine, workflow, goal):
    async def planning(state):
        return await prepare(engine, workflow, goal)
    async def tasks(state):
        return await wave(engine, workflow, goal)
    async def verification(state):
        return await finalize(engine, workflow, goal)
    graph = StateGraph(GraphState)
    graph.add_node("planning", planning)
    graph.add_node("task_wave", tasks)
    graph.add_node("verification", verification)
    graph.add_edge(START, "planning")
    graph.add_edge("planning", "task_wave")
    graph.add_conditional_edges("task_wave", lambda state: "verification" if state["complete"] else "task_wave",
                                {"verification": "verification", "task_wave": "task_wave"})
    graph.add_edge("verification", END)
    return graph.compile()
