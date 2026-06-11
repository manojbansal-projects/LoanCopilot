"""Text chunking with configurable size and overlap."""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from deployment.config import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP


_PRODUCT_LABEL = {
    "home_loan":     "Home Loan Policy",
    "personal_loan": "Personal Loan Policy",
    "msme_loan":     "MSME Loan Policy",
    "car_loan":      "New Car Loan Policy",
    "faq":           "General FAQ",
}


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split documents into chunks; inherit source metadata on every chunk.

    Each chunk is prefixed with its product label so retrieval stays
    product-aware even after text is split away from section headings.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        label = _PRODUCT_LABEL.get(chunk.metadata.get("product", ""), "")
        if label:
            chunk.page_content = f"[{label}]\n{chunk.page_content}"
    return chunks
