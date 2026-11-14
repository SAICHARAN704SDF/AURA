"""Transient graph control; durable task state remains in SQLite memory."""
from typing import TypedDict

class GraphState(TypedDict):
    complete: bool
