"""
FILE: backend/src/aura/orchestration/workflow/persistence.py
PURPOSE: Keep the historical Memory import path compatible.
MAIN RESPONSIBILITY: Persistence Compatibility Export.
INPUTS: Imports from the old workflow persistence path.
OUTPUTS: The shared Memory class.
IMPORTANT FUNCTIONS / CLASSES: Module constants / compatibility exports.
CONNECTED MODULES: aura.memory.manager.
WHERE THIS FILE IS USED: backend/src/aura/api/application.py.
PRESENTATION EXPLANATION: "This is an intentional compatibility export, not a duplicate database implementation."
"""
# PRESENTATION SECTION: PERSISTENCE COMPATIBILITY EXPORT
from aura.memory.manager import Memory

__all__ = ["Memory"]
