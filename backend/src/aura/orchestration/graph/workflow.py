"""
FILE: backend/src/aura/orchestration/graph/workflow.py
PURPOSE: Compile planning, task-wave and verification nodes with conditional routing.
MAIN RESPONSIBILITY: Langgraph Topology.
INPUTS: Engine, workflow state and goal.
OUTPUTS: Compiled LangGraph.
IMPORTANT FUNCTIONS / CLASSES: build_graph.
CONNECTED MODULES: langgraph.graph.
WHERE THIS FILE IS USED: backend/src/aura/orchestration/workflow/engine.py.
PRESENTATION EXPLANATION: "Task waves repeat until dependencies are completed, then verification runs."
"""
# PRESENTATION SECTION: LANGGRAPH TOPOLOGY
from langgraph.graph import END, START, StateGraph
from .state import GraphState
from .nodes import prepare, wave, finalize


def build_graph(engine, workflow, goal, checkpointer=None):
    """Purpose: LangGraph topology.
    
    Inputs: Engine, workflow and goal.
    Process and rationale: Bind planning, task_wave and verification nodes; loop while tasks remain and terminate after verification.
    Returns: Compiled StateGraph.
    """
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
    return graph.compile(checkpointer=checkpointer)
