"""Recall recent accepted reports by meaning, within the current source and project scope."""
import json

from aura.rag.retrieval.ranking import cosine


def store_episode(memory, workflow, goal, summary, embedding_model, vector):
    with memory.db:
        memory.db.execute("""
            INSERT OR REPLACE INTO research_episodes(workflow, project, sources, question, summary, model, vector)
            VALUES (?,?,?,?,?,?,?)
        """, (workflow, goal.project_id, json.dumps(sorted(goal.document_ids)), goal.goal,
              summary[:1500], embedding_model, json.dumps(vector)))


def recent_episodes(memory, goal, model):
    # Exact source-set matching prevents reintroducing evidence from a deselected paper.
    return memory.db.execute("""
        SELECT workflow,question,summary,vector FROM research_episodes
        WHERE project=? AND sources=? AND model=? ORDER BY rowid DESC LIMIT 200
    """, (goal.project_id, json.dumps(sorted(goal.document_ids)), model)).fetchall()


def nearest(rows, query_vector, k=3):
    scored = [(cosine(query_vector, json.loads(vector)), workflow, question, summary)
              for workflow, question, summary, vector in rows]
    return [{"workflow": w, "question": q, "summary": s, "similarity": score}
            for score, w, q, s in sorted(scored, reverse=True)[:k] if score>0.25]
