from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.llm.client import get_embeddings


def build_vector_store(documents: list[Document]) -> FAISS:
    embeddings = get_embeddings()
    return FAISS.from_documents(documents, embeddings)


def save_vector_store(vector_store: FAISS, target_dir: str) -> None:
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    vector_store.save_local(target_dir)


def load_vector_store(target_dir: str) -> FAISS:
    embeddings = get_embeddings()
    return FAISS.load_local(
        target_dir,
        embeddings,
        allow_dangerous_deserialization=True,
    )
