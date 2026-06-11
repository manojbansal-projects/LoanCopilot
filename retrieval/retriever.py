"""Top-level retrieval interface used by tools and the agent."""
from __future__ import annotations
from langchain.schema import Document
from retrieval.chroma_store import load_store
from deployment.config import RAG_TOP_K

_store = None


def _get_store():
    global _store
    if _store is None:
        _store = load_store()
    return _store


def retrieve(query: str, k: int = RAG_TOP_K) -> list[Document]:
    """Return the top-k most relevant document chunks for a query."""
    return _get_store().similarity_search(query, k=k)
