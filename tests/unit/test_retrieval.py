"""
Unit tests — Retriever and Reranker
Tests hybrid retrieval fusion logic and cross-encoder reranking.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models.schemas import ChunkMetadata, RetrievedChunk
from app.rag.retriever import HybridRetriever


# ── Fixtures ───────────────────────────────────────────────────────────────────

def make_chunk(
    chunk_id: str,
    content: str,
    source: str = "test.pdf",
    page: int = 1,
    semantic_score: float | None = None,
    bm25_score: float | None = None,
) -> RetrievedChunk:
    """Helper to construct a RetrievedChunk for testing."""
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=content,
        metadata=ChunkMetadata(
            source=source,
            page=page,
            chunk_id=chunk_id,
            document_id="doc_abc",
        ),
        semantic_score=semantic_score,
        bm25_score=bm25_score,
    )


# ── RRF tests ──────────────────────────────────────────────────────────────────

class TestReciprocalRankFusion:
    """Tests for the static _reciprocal_rank_fusion helper."""

    def test_basic_fusion(self) -> None:
        """Chunks appearing in both lists should receive higher fused scores."""
        list1 = [
            make_chunk("a", "Revenue increased by 20%"),
            make_chunk("b", "Operating costs declined"),
            make_chunk("c", "New product launched"),
        ]
        list2 = [
            make_chunk("b", "Operating costs declined"),
            make_chunk("a", "Revenue increased by 20%"),
            make_chunk("d", "Unrelated chunk"),
        ]
        result = HybridRetriever._reciprocal_rank_fusion(list1, list2)

        # Chunks a and b appear in both lists — they should outrank c and d
        result_ids = [c.chunk_id for c in result]
        assert result_ids.index("a") < result_ids.index("d")
        assert result_ids.index("b") < result_ids.index("d")

    def test_deduplication(self) -> None:
        """Each chunk_id should appear exactly once in the fused result."""
        list1 = [make_chunk("x", "content")]
        list2 = [make_chunk("x", "content")]
        result = HybridRetriever._reciprocal_rank_fusion(list1, list2)
        ids = [c.chunk_id for c in result]
        assert len(ids) == len(set(ids))

    def test_empty_lists(self) -> None:
        result = HybridRetriever._reciprocal_rank_fusion([], [])
        assert result == []

    def test_single_list(self) -> None:
        chunk = make_chunk("solo", "Only in one list")
        result = HybridRetriever._reciprocal_rank_fusion([chunk])
        assert len(result) == 1
        assert result[0].chunk_id == "solo"

    def test_rrf_scores_positive(self) -> None:
        """All fused scores should be positive."""
        chunks = [make_chunk(str(i), f"Content {i}") for i in range(5)]
        result = HybridRetriever._reciprocal_rank_fusion(chunks)
        for c in result:
            assert (c.semantic_score or 0) > 0


# ── Reranker tests ─────────────────────────────────────────────────────────────

class TestReranker:
    def test_reranker_top_k_limits_output(self) -> None:
        """Reranker should return at most top_k chunks."""
        from app.rag.reranker import Reranker

        reranker = Reranker(top_k=3)

        # Mock the cross-encoder model
        mock_model = MagicMock()
        import numpy as np
        mock_model.predict.return_value = np.array([0.9, 0.7, 0.5, 0.3, 0.1])
        reranker._model = mock_model

        chunks = [make_chunk(f"c{i}", f"Content {i}") for i in range(5)]
        result = reranker.rerank("query", chunks, top_k=3)

        assert len(result) == 3

    def test_reranker_assigns_scores(self) -> None:
        """Each returned chunk should have a rerank_score set."""
        from app.rag.reranker import Reranker
        import numpy as np

        reranker = Reranker(top_k=2)
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.8, 0.4])
        reranker._model = mock_model

        chunks = [make_chunk("a", "First"), make_chunk("b", "Second")]
        result = reranker.rerank("test query", chunks)

        for chunk in result:
            assert chunk.rerank_score is not None

    def test_reranker_assigns_ranks(self) -> None:
        """final_rank should be 1-indexed and ordered."""
        from app.rag.reranker import Reranker
        import numpy as np

        reranker = Reranker(top_k=3)
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.3, 0.9, 0.6])
        reranker._model = mock_model

        chunks = [make_chunk(f"c{i}", f"Content {i}") for i in range(3)]
        result = reranker.rerank("test", chunks)

        ranks = [c.final_rank for c in result]
        assert ranks == [1, 2, 3]

    def test_reranker_empty_input(self) -> None:
        """Empty input should return empty output without error."""
        from app.rag.reranker import Reranker

        reranker = Reranker()
        result = reranker.rerank("query", [])
        assert result == []


# ── HybridRetriever tests (with mocked vector store) ──────────────────────────

class TestHybridRetriever:
    @pytest.fixture
    def mock_store(self):
        store = MagicMock()
        store.count.return_value = 10
        store.search.return_value = [
            make_chunk("sem_1", "Semantic result one", semantic_score=0.9),
            make_chunk("sem_2", "Semantic result two", semantic_score=0.7),
        ]
        store.get_all_documents_metadata.return_value = [
            {"source": "test.pdf", "page": "1", "chunk_id": "sem_1", "document_id": "doc_abc"},
            {"source": "test.pdf", "page": "1", "chunk_id": "sem_2", "document_id": "doc_abc"},
        ]
        store._collection = MagicMock()
        store._collection.get.return_value = {
            "ids": ["sem_1", "sem_2"],
            "documents": ["Semantic result one", "Semantic result two"],
            "metadatas": [
                {"source": "test.pdf", "page": "1", "chunk_id": "sem_1", "document_id": "doc_abc"},
                {"source": "test.pdf", "page": "1", "chunk_id": "sem_2", "document_id": "doc_abc"},
            ],
        }
        return store

    def test_retrieve_returns_list(self, mock_store) -> None:
        retriever = HybridRetriever(vector_store=mock_store)
        results = retriever.retrieve("test query", top_k=5)
        assert isinstance(results, list)

    def test_retrieve_calls_semantic_search(self, mock_store) -> None:
        retriever = HybridRetriever(vector_store=mock_store)
        retriever.retrieve("test query")
        mock_store.search.assert_called_once()

    def test_retrieve_empty_store_returns_empty(self) -> None:
        store = MagicMock()
        store.count.return_value = 0
        retriever = HybridRetriever(vector_store=store)
        results = retriever.retrieve("anything")
        assert results == []
