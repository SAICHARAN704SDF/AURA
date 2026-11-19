"""
FILE: backend/scripts/init_db.py
PURPOSE: Initialize missing workflow tables without resetting data.
MAIN RESPONSIBILITY: Local entry point.
INPUTS: Settings.data_dir from the local configuration.
OUTPUTS: Existing or newly initialized workflows.sqlite.
IMPORTANT FUNCTIONS: __main__ entry block.
CONNECTED MODULES: aura.core.settings, aura.database.connection
WHERE THIS FILE IS USED: Manual startup/setup from the repository root.
PRESENTATION EXPLANATION: "This setup command creates missing tables; it does not replace the database."
"""
# PRESENTATION SECTION: DATABASE SETUP
from pathlib import Path
from aura.core import Settings
from aura.database.connection import open_workflow_database

if __name__ == "__main__":
    directory = Path(Settings().data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    db = open_workflow_database(directory / "workflows.sqlite")
    db.close()
    print("Workflow database ready. RAG storage initializes on API startup.")
