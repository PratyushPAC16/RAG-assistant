"""
Integration tests — FastAPI endpoints
Tests the full HTTP layer using FastAPI's TestClient with mocked agent dependencies.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── We must set required env vars before importing settings ───────────────────
import os

os.environ.setdefault("GOOGLE_API_KEY", "test_google_key")
os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")

from app.api.main import app, _document_registry
from app.models.schemas import (
    AgentState,
    AgentType,
    SourceCitation,
)


# ── Test client fixture ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the in-memory document registry between tests."""
    _document_registry.clear()
    yield
    _document_registry.clear()


@pytest.fixture
def client():
    """TestClient with all external dependencies pre-mocked at session scope."""
    with TestClient(app) as c:
        yield c


# ── Mock orchestrator factory ──────────────────────────────────────────────────

def _mock_orchestrator(answer: str = "Test answer", agent: AgentType = AgentType.RAG):
    """Create a mock orchestrator that returns a predefined AgentState."""
    mock = MagicMock()
    result = AgentState(
        query="test",
        answer=answer,
        sources=[SourceCitation(document="report.pdf", page=1)],
        agent_type=agent,
        latency_ms={"retrieval": 50.0, "llm": 200.0, "total": 260.0},
    )
    mock.run.return_value = result
    return mock


# ── Health endpoint tests ──────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        with patch("app.api.main.get_vector_store") as mock_vs:
            mock_vs.return_value.count.return_value = 42
            response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_schema(self, client: TestClient) -> None:
        with patch("app.api.main.get_vector_store") as mock_vs:
            mock_vs.return_value.count.return_value = 10
            response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "documents_indexed" in data
        assert data["status"] == "healthy"


# ── Document list tests ────────────────────────────────────────────────────────

class TestDocumentsEndpoint:
    def test_empty_document_list(self, client: TestClient) -> None:
        response = client.get("/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []

    def test_document_list_after_upload(self, client: TestClient) -> None:
        # Manually insert a record
        from app.models.schemas import DocumentRecord, DocumentStatus, FileType
        from datetime import datetime

        doc_id = uuid.uuid4().hex
        _document_registry[doc_id] = DocumentRecord(
            document_id=doc_id,
            filename="test.txt",
            file_type=FileType.TXT,
            status=DocumentStatus.INDEXED,
            num_chunks=5,
        )
        response = client.get("/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "test.txt"


# ── Upload endpoint tests ──────────────────────────────────────────────────────

class TestUploadEndpoint:
    def test_unsupported_file_type_returns_415(self, client: TestClient) -> None:
        response = client.post(
            "/upload",
            files={"file": ("image.png", b"fake content", "image/png")},
        )
        assert response.status_code == 415

    def test_txt_upload_success(self, client: TestClient, patch_external_services) -> None:
        """Test uploading a TXT file with mocked vector store and processor."""
        txt_content = b"This is a test document with some content for RAG testing."

        from app.models.schemas import ChunkMetadata
        from langchain_core.documents import Document

        chunk_meta = ChunkMetadata(
            source="test.txt",
            page=1,
            chunk_id="chunk_abc123",
            document_id="doc_xyz",
        )
        mock_doc = Document(page_content="Test content", metadata=chunk_meta.model_dump())

        mock_processor_instance = MagicMock()
        mock_processor_instance.process.return_value = ([mock_doc], [chunk_meta])

        # Configure the session-level mocks
        patch_external_services["vector_store"].add_documents.return_value = ["chunk_abc123"]
        patch_external_services["retriever"].refresh_bm25_index.return_value = None

        with patch("app.api.main.DocumentProcessor", return_value=mock_processor_instance):
            response = client.post(
                "/upload",
                files={"file": ("test.txt", txt_content, "text/plain")},
            )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["status"] == "indexed"
        assert data["num_chunks"] == 1


# ── Chat endpoint tests ────────────────────────────────────────────────────────

class TestChatEndpoint:
    def test_chat_basic_request(self, client: TestClient) -> None:
        with patch("app.api.main.get_orchestrator") as mock_orch:
            mock_orch.return_value = _mock_orchestrator("This is the answer.")

            response = client.post(
                "/chat",
                json={"query": "What is the revenue?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is the answer."
        assert "session_id" in data
        assert "sources" in data

    def test_chat_empty_query_rejected(self, client: TestClient) -> None:
        response = client.post("/chat", json={"query": "   "})
        # strip_query validator raises ValueError → Pydantic returns 422
        assert response.status_code == 422

    def test_chat_session_continuity(self, client: TestClient) -> None:
        """Passing a session_id should return the same session_id."""
        session = "test_session_abc"
        with patch("app.api.main.get_orchestrator") as mock_orch:
            mock_orch.return_value = _mock_orchestrator()
            response = client.post(
                "/chat",
                json={"query": "Tell me more", "session_id": session},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session

    def test_chat_returns_latency(self, client: TestClient) -> None:
        with patch("app.api.main.get_orchestrator") as mock_orch:
            mock_orch.return_value = _mock_orchestrator()
            response = client.post("/chat", json={"query": "Test question"})
        data = response.json()
        assert "latency_ms" in data


# ── Delete endpoint tests ──────────────────────────────────────────────────────

class TestDeleteEndpoint:
    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.delete("/documents/nonexistent_id")
        assert response.status_code == 404

    def test_delete_existing_document(self, client: TestClient) -> None:
        from app.models.schemas import DocumentRecord, DocumentStatus, FileType

        doc_id = uuid.uuid4().hex
        _document_registry[doc_id] = DocumentRecord(
            document_id=doc_id,
            filename="to_delete.txt",
            file_type=FileType.TXT,
            status=DocumentStatus.INDEXED,
            num_chunks=3,
        )

        with (
            patch("app.api.main.get_vector_store") as mock_vs,
            patch("app.api.main.get_retriever") as mock_ret,
        ):
            mock_vs.return_value.delete_by_document_id.return_value = 3
            mock_ret.return_value.refresh_bm25_index.return_value = None

            response = client.delete(f"/documents/{doc_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert data["chunks_deleted"] == 3
        assert doc_id not in _document_registry
