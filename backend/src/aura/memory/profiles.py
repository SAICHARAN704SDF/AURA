"""Project preferences and section feedback in the existing document metadata database."""
from pydantic import BaseModel, Field
from typing import Literal


class Profile(BaseModel):
    preferences: str = Field(default='', max_length=500)
    adaptive_retrieval: bool = False


class Feedback(BaseModel):
    document_id: str = Field(min_length=1, max_length=64)
    section: str = Field(min_length=1, max_length=120, pattern=r'\S')
    vote: Literal[-1, 1]


class Profiles:
    def __init__(self, db):
        self.db = db
        db.executescript("""
        CREATE TABLE IF NOT EXISTS project_profiles(project TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS source_feedback(project TEXT, document TEXT, section TEXT,
            vote INTEGER CHECK(vote IN(-1,1)), PRIMARY KEY(project,document,section));
        """)

    def get(self, project):
        row = self.db.execute("SELECT body FROM project_profiles WHERE project=?", (project,)).fetchone()
        return Profile.model_validate_json(row[0]) if row else Profile()

    def save(self, project, profile):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO project_profiles VALUES (?,?)", (project, profile.model_dump_json()))
        return profile

    def vote(self, project, feedback):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO source_feedback VALUES (?,?,?,?)",
                            (project, feedback.document_id, feedback.section.strip(), feedback.vote))
        return feedback

    def rank(self, project, candidates):
        """Allow a preference to break near ties, with at most one rank of displacement."""
        scores = dict(self.db.execute("SELECT document, AVG(vote) FROM source_feedback WHERE project=? GROUP BY document",
                                     (project,)))
        ranked = sorted(enumerate(candidates), key=lambda pair: pair[0] - 0.6 * scores.get(pair[1].document_id, 0))
        return [candidate for _, candidate in ranked]
