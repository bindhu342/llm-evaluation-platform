import os
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.rag.embeddings import get_embeddings


INDEX_PATH = os.getenv("VECTOR_STORE_PATH", "./data/faiss_index")

_store: FAISS | None = None


def get_vector_store() -> FAISS | None:
    """
    Load the existing FAISS vector store.

    Returns None when no index has been created yet.
    """
    global _store

    if _store is not None:
        return _store

    if not os.path.exists(INDEX_PATH):
        return None

    embeddings = get_embeddings()

    _store = FAISS.load_local(
        INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )

    return _store


def add_documents(docs: List[Document]) -> None:
    """
    Add document chunks to the FAISS vector store
    and persist the index to disk.
    """
    global _store

    if not docs:
        return

    embeddings = get_embeddings()

    if _store is None:
        if os.path.exists(INDEX_PATH):
            _store = FAISS.load_local(
                INDEX_PATH,
                embeddings,
                allow_dangerous_deserialization=True,
            )
            _store.add_documents(docs)
        else:
            _store = FAISS.from_documents(
                docs,
                embeddings,
            )
    else:
        _store.add_documents(docs)

    directory = os.path.dirname(INDEX_PATH) or "."
    os.makedirs(directory, exist_ok=True)

    _store.save_local(INDEX_PATH)