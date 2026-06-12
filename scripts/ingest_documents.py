"""
Step 1 of 2 in knowledge base setup:
Load raw policy docs → chunk → embed → persist to ChromaDB.
Run this once before starting the agent.

Usage:
    python scripts/ingest_documents.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.document_loader import load_documents
from retrieval.chunker import chunk_documents
from retrieval.chroma_store import build_store


def main():
    print("Loading policy documents…")
    docs = load_documents()
    print(f"  Loaded {len(docs)} documents")

    print("Chunking…")
    chunks = chunk_documents(docs)
    print(f"  Created {len(chunks)} chunks")

    print("Embedding and persisting to ChromaDB…")
    store = build_store(chunks)
    print(f"  Done. Collection: {store._collection.name}")


if __name__ == "__main__":
    main()
