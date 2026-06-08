"""
Integration test configuration.

Patches heavy singletons (EmbeddingService, ChromaDB, LLM clients, Tavily)
at module-import time so that FastAPI's lifespan startup never touches the
real Google / Tavily APIs.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# ── Make sure env vars exist before any app imports ────────────────────────────
os.environ.setdefault("GOOGLE_API_KEY", "test_google_key")
os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")


# ---------------------------------------------------------------------------
# Session-scoped patches — applied before *any* app module is imported so
# the lifespan never touches the real Google / Tavily / ChromaDB APIs.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def patch_external_services():
    """
    Patch all external-service constructors for the entire test session.
    This prevents EmbeddingService, VectorStore, and AgentOrchestrator
    from hitting real APIs during TestClient startup (lifespan).
    """
    mock_embedding_service = MagicMock()
    mock_embedding_service.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embedding_service.get_langchain_embeddings.return_value = MagicMock()

    mock_vector_store = MagicMock()
    mock_vector_store.count.return_value = 0
    mock_vector_store.add_documents.return_value = []
    mock_vector_store.delete_by_document_id.return_value = 0
    mock_vector_store.search.return_value = []

    mock_retriever = MagicMock()
    mock_retriever.refresh_bm25_index.return_value = None

    mock_orchestrator = MagicMock()

    with (
        patch("app.rag.embeddings.get_embedding_service", return_value=mock_embedding_service),
        patch("app.rag.vector_store.get_embedding_service", return_value=mock_embedding_service),
        patch("app.rag.vector_store.chromadb.PersistentClient"),
        patch("app.api.main.get_vector_store", return_value=mock_vector_store),
        patch("app.api.main.get_retriever", return_value=mock_retriever),
        patch("app.api.main.get_orchestrator", return_value=mock_orchestrator),
    ):
        yield {
            "embedding_service": mock_embedding_service,
            "vector_store": mock_vector_store,
            "retriever": mock_retriever,
            "orchestrator": mock_orchestrator,
        }
