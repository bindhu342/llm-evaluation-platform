import pytest
from unittest.mock import patch, MagicMock
from backend.rag.retriever import retrieve


@patch("backend.rag.retriever.get_vector_store")
def test_retrieve_returns_strings(mock_store):
    mock_doc = MagicMock()
    mock_doc.page_content = "AWS Lambda is a serverless compute service."
    mock_store.return_value.similarity_search.return_value = [mock_doc]

    results = retrieve("What is Lambda?", k=1)

    assert isinstance(results, list)
    assert len(results) == 1
    assert "Lambda" in results[0]


@patch("backend.rag.retriever.get_vector_store")
def test_retrieve_respects_k(mock_store):
    mock_store.return_value.similarity_search.return_value = []
    retrieve("query", k=3)
    mock_store.return_value.similarity_search.assert_called_once_with("query", k=3)


@patch("backend.rag.retriever.get_vector_store")
def test_retrieve_empty_results(mock_store):
    mock_store.return_value.similarity_search.return_value = []
    results = retrieve("unknown query", k=4)
    assert results == []
