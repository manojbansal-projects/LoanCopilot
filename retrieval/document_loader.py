"""Load raw policy documents from knowledge/raw/."""
from pathlib import Path
from langchain_core.documents import Document
from deployment.config import KNOWLEDGE_BASE_PATH

PRODUCT_MAP = {
    "home_loan_policy.txt":     "home_loan",
    "personal_loan_policy.txt": "personal_loan",
    "msme_loan_policy.txt":     "msme_loan",
    "car_loan_policy.txt":      "car_loan",
    "general_faq.txt":          "faq",
}


def load_documents() -> list[Document]:
    """Load all .txt policy files and return LangChain Document objects with metadata."""
    docs = []
    for filename, product in PRODUCT_MAP.items():
        path = Path(KNOWLEDGE_BASE_PATH) / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        docs.append(Document(
            page_content=text,
            metadata={"source": filename, "product": product},
        ))
    return docs
