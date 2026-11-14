"""Idempotent initialization of the existing workflow schema."""
import sqlite3
from pathlib import Path

def open_workflow_database(path: Path):
    db=sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY, project TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS workflows(id TEXT PRIMARY KEY, project TEXT, goal TEXT, state TEXT, body TEXT, updated REAL);
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, workflow TEXT, project TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS memory(workflow TEXT, project TEXT, layer TEXT, key TEXT, body TEXT, PRIMARY KEY(workflow,project,layer,key));
    ''')
    db.commit()
    return db
