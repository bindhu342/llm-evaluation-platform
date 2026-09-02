import os
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from backend.rag.embeddings import get_embeddings

INDEX_PATH = os.getenv("VECTOR_STORE_PATH", "./data/faiss_index")
_store: FAISS | None = None


def _get_store() -> FAISS:
    global _store
    if _store is None:
        embeddings = get_embeddings()
        if os.path.exists(INDEX_PATH):
            _store = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        else:
            _store = FAISS.from_texts(["init"], embeddings)
    return _store


def add_documents(docs: List[Document]) -> None:
    store = _get_store()
    store.add_documents(docs)
    store.save_local(INDEX_PATH)


def get_vector_store() -> FAISS:
    return _get_store()
