"""
Enterprise Agentic RAG Assistant
Reranker — uses a cross-encoder model to score query-chunk pairs and
return only the most relevant chunks.

Model: cross-encoder/ms-marco-MiniLM-L6-v2
Pipeline: 20 retrieved chunks → cross-encoder → top-5 chunks
"""

from __future__ import annotations

import threading

from sentence_transformers.cross_encoder import CrossEncoder

from app.models.schemas import RetrievedChunk
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


class Reranker:
    """
    Cross-encoder reranker that scores (query, passage) pairs and reorders
    retrieved chunks by relevance.

    The cross-encoder reads the full query and chunk together, producing a
    much higher-quality relevance signal than bi-encoder similarity scores.

    Attributes:
        model_name: HuggingFace model identifier for the cross-encoder.
        top_k:      Number of chunks to return after reranking.
    """

    # Class-level lock to prevent concurrent model downloads
    _model_lock = threading.Lock()

    def __init__(
        self,
        model_name: str | None = None,
        top_k: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.reranker_model
        self.top_k = top_k or settings.reranker_top_k
        self._model: CrossEncoder | None = None
        logger.info(
            "Reranker configured",
            extra={"model": self.model_name, "top_k": self.top_k},
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Score each (query, chunk) pair and return the top-K chunks.

        Args:
            query:  The user's search query.
            chunks: List of retrieved chunks (typically 20 from hybrid retrieval).
            top_k:  Override for how many chunks to return.

        Returns:
            Reranked list of chunks (length ≤ *top_k*) with:
            - ``rerank_score``: Cross-encoder logit score (higher = more relevant).
            - ``final_rank``: 1-indexed rank after reranking.

        Raises:
            RuntimeError: If the cross-encoder model cannot be loaded.
        """
        k = top_k or self.top_k

        if not chunks:
            return []

        model = self._load_model()

        # Prepare (query, passage) pairs for the cross-encoder
        pairs = [(query, chunk.content) for chunk in chunks]

        with log_latency(
            logger,
            "reranking",
            num_candidates=len(chunks),
            top_k=k,
            model=self.model_name,
        ):
            scores: list[float] = model.predict(pairs).tolist()  # type: ignore[union-attr]

        # Attach scores and sort by descending score
        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = round(float(score), 6)

        reranked = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)

        # Assign final ranks and slice to top_k
        results: list[RetrievedChunk] = []
        for rank, chunk in enumerate(reranked[:k], start=1):
            chunk.final_rank = rank
            results.append(chunk)

        logger.info(
            "Reranking complete",
            extra={
                "query": query[:80],
                "candidates": len(chunks),
                "returned": len(results),
                "top_score": results[0].rerank_score if results else None,
            },
        )
        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_model(self) -> CrossEncoder:
        """
        Lazily load the cross-encoder model, thread-safely.
        The model is kept in memory after first load to avoid repeated downloads.
        """
        if self._model is not None:
            return self._model

        with self._model_lock:
            # Double-checked locking
            if self._model is not None:
                return self._model

            logger.info(
                "Loading cross-encoder model (first call may download weights)",
                extra={"model": self.model_name},
            )
            try:
                self._model = CrossEncoder(
                    model_name=self.model_name,
                    max_length=512,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load cross-encoder '{self.model_name}': {exc}"
                ) from exc

            logger.info(
                "Cross-encoder model loaded",
                extra={"model": self.model_name},
            )
            return self._model


# ── Module-level singleton ─────────────────────────────────────────────────────

_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    """
    Return the singleton :class:`Reranker` instance.
    The cross-encoder model is loaded lazily on the first :meth:`rerank` call.
    """
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
