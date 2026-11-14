"""Initialize missing workflow tables without resetting existing data."""
from pathlib import Path
from aura.core import Settings
from aura.database.connection import open_workflow_database

if __name__ == "__main__":
    directory = Path(Settings().data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    db = open_workflow_database(directory / "workflows.sqlite")
    db.close()
    print("Workflow database ready. RAG storage initializes on API startup.")
