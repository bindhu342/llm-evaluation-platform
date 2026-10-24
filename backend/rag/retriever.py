from typing import List

from backend.rag.vector_store import get_vector_store


def retrieve(query: str, k: int = 4) -> List[str]:
    """
    Retrieve relevant text chunks from the FAISS vector store.

    Returns:
        List[str]: Retrieved document contents.
    """
    store = get_vector_store()

    if store is None:
        return []

    if not query or not query.strip():
        return []

    documents = store.similarity_search(query, k=k)

    return [document.page_content for document in documents]