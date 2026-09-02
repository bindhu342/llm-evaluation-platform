from typing import List
from backend.rag.vector_store import get_vector_store


def retrieve(query: str, k: int = 4) -> List[str]:
    store = get_vector_store()
    docs = store.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]
