"""
FILE: backend/src/aura/database/connection.py
PURPOSE: Open the workflow database and create missing tables idempotently.
MAIN RESPONSIBILITY: Sqlite Schema.
INPUTS: SQLite path.
OUTPUTS: Connection with goals, workflows, events and memory tables.
IMPORTANT FUNCTIONS / CLASSES: open_workflow_database.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: backend/src/aura/memory/manager.py.
PRESENTATION EXPLANATION: "Initialization creates missing tables without resetting existing records."
"""
# PRESENTATION SECTION: SQLITE SCHEMA
import sqlite3
from pathlib import Path

def open_workflow_database(path: Path):
    """Purpose: Database initialization.
    
    Inputs: SQLite filesystem path.
    Process and rationale: Open SQLite in WAL mode and create missing goals/workflows/events/memory tables without dropping existing records.
    Returns: SQLite connection.
    """
    db=sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY, project TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS workflows(id TEXT PRIMARY KEY, project TEXT, goal TEXT, state TEXT, body TEXT, updated REAL);
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, workflow TEXT, project TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS research_episodes(workflow TEXT PRIMARY KEY, project TEXT NOT NULL, sources TEXT NOT NULL,
        question TEXT NOT NULL, summary TEXT NOT NULL, model TEXT NOT NULL, vector TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS episodes_by_scope ON research_episodes(project,sources,model);
    CREATE TABLE IF NOT EXISTS memory(workflow TEXT, project TEXT, layer TEXT, key TEXT, body TEXT, PRIMARY KEY(workflow,project,layer,key));
    ''')
    db.commit()
    return db
