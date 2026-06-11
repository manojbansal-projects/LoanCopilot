"""ChromaDB persistent vector store (project uses ChromaDB per spec, not FAISS)."""
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.documents import Document
from retrieval.embedder import get_embeddings
from deployment.config import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME


def build_store(chunks: list[Document]) -> Chroma:
    """Embed chunks and persist to disk. Overwrites any existing collection."""
    return Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=str(CHROMA_DB_PATH),
    )


def load_store() -> Chroma:
    """Load an already-persisted ChromaDB collection."""
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DB_PATH),
    )
