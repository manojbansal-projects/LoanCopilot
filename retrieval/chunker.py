"""Text chunking with configurable size and overlap."""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from deployment.config import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split documents into chunks; inherit source metadata on every chunk."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,          # 500 tokens (chars as proxy)
        chunk_overlap=RAG_CHUNK_OVERLAP,    # 100 token overlap
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)
