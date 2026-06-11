"""OpenAI embedding wrapper."""
from langchain_openai import OpenAIEmbeddings
from deployment.config import EMBEDDING_MODEL


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)
