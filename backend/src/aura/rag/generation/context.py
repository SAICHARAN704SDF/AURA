"""
FILE: backend/src/aura/rag/generation/context.py
PURPOSE: Preserve retrieved text through LangChain-core Document objects.
MAIN RESPONSIBILITY: Langchain Document Context.
INPUTS: Retrieved Chunk records.
OUTPUTS: Chunk IDs and unchanged source text for prompting.
IMPORTANT FUNCTIONS / CLASSES: evidence_payload.
CONNECTED MODULES: aura.observability.events, langchain_core.documents.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "LangChain is used at the document boundary; LangGraph separately coordinates agents."
"""
# PRESENTATION SECTION: LANGCHAIN DOCUMENT CONTEXT
from aura.observability.events import traced, emit, span
from langchain_core.documents import Document


@traced('context_assembly')
def evidence_payload(chunks):
    """Purpose: LangChain context.
    
    Inputs: Retrieved chunks.
    Process and rationale: Construct LangChain-core Documents preserving text/metadata, then expose chunk IDs and unchanged text to generation.
    Returns: List of evidence dictionaries.
    """
    documents = [Document(page_content=c.text, metadata=c.model_dump(exclude={"text"})) for c in chunks]
    return [{"chunk_id":d.metadata["id"], "text":d.page_content} for d in documents]
