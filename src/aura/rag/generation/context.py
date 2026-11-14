"""Lossless LangChain document boundary for retrieved evidence."""
from aura.observability.events import traced, emit, span
from langchain_core.documents import Document


@traced('context_assembly')
def evidence_payload(chunks):
    documents = [Document(page_content=c.text, metadata=c.model_dump(exclude={"text"})) for c in chunks]
    return [{"chunk_id":d.metadata["id"], "text":d.page_content} for d in documents]
