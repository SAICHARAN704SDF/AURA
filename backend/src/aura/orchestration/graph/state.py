"""
FILE: backend/src/aura/orchestration/graph/state.py
PURPOSE: Define the control-state shape exchanged by LangGraph nodes.
MAIN RESPONSIBILITY: Graph State.
INPUTS: Completion flag from graph nodes.
OUTPUTS: Typed GraphState structure.
IMPORTANT FUNCTIONS / CLASSES: GraphState.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "The graph control flag is separate from durable task details in SQLite."
"""
# PRESENTATION SECTION: GRAPH STATE
from typing import TypedDict

class GraphState(TypedDict):
    complete: bool
