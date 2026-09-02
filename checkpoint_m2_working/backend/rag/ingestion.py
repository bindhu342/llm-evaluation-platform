from langchain_community.document_loaders import TextLoader, PyPDFLoader
from backend.rag.chunking import chunk_documents
from backend.rag.vector_store import add_documents


def ingest_file(file_path: str) -> int:
    loader = PyPDFLoader(file_path) if file_path.endswith(".pdf") else TextLoader(file_path)
    docs = loader.load()
    chunks = chunk_documents(docs)
    add_documents(chunks)
    return len(chunks)
