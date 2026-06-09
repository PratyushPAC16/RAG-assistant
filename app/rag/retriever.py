"""
Enterprise Agentic RAG Assistant
Hybrid retrieval pipeline — production-grade implementation fusing:
  1. Semantic search (ChromaDB vector store)
  2. Keyword search (BM25Okapi via rank-bm25)
  3. Reciprocal Rank Fusion (RRF) with configurable per-stream weights
  4. Cross-encoder reranking (handled by app.rag.reranker)

Each stage emits detailed timing and score-distribution metrics to support
the observability dashboard.

Pipeline:
    Query
      ↓
    Vector Search (ChromaDB, top-30)   BM25 Search (top-30)
              ↘                        ↙
            Reciprocal Rank Fusion (RRF)
                      ↓
              Cross-Encoder Reranker (top-30 → top-5)
                      ↓
                  Top Context → LLM
"""

from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi

from app.models.schemas import RetrievedChunk, ScoreDistribution
from app.rag.vector_store import VectorStore, get_vector_store
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


# ── Retrieval result container ─────────────────────────────────────────────────

@dataclass
class RetrievalResult:
    """
    Full output of one hybrid retrieval pass, including the merged chunk
    list and all per-stage observability metrics.

    This is the return type of :meth:`HybridRetriever.retrieve_with_metrics`.
    The simpler :meth:`HybridRetriever.retrieve` method just returns
    ``result.chunks``.
    """
    chunks: list[RetrievedChunk] = field(default_factory=list)

    # ── Per-stage chunk counts ─────────────────────────────────────
    num_vector_results: int = 0
    num_bm25_results: int = 0
    num_fused_results: int = 0          # After RRF, before slice

    # ── Per-stage latencies (ms) ───────────────────────────────────
    vector_search_latency_ms: float = 0.0
    bm25_search_latency_ms: float = 0.0
    rrf_fusion_latency_ms: float = 0.0
    total_retrieval_latency_ms: float = 0.0

    # ── Score distributions per stage ──────────────────────────────
    vector_score_dist: ScoreDistribution = field(default_factory=ScoreDistribution)
    bm25_score_dist: ScoreDistribution = field(default_factory=ScoreDistribution)
    rrf_score_dist: ScoreDistribution = field(default_factory=ScoreDistribution)


# ── Score distribution helper ──────────────────────────────────────────────────

def _compute_score_distribution(scores: list[float]) -> ScoreDistribution:
    """
    Compute min, max, mean, P50, and P90 from a list of scores.
    Returns an empty ScoreDistribution if the list is empty.
    """
    if not scores:
        return ScoreDistribution()
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    p50 = statistics.median(sorted_scores)
    p90_idx = max(0, int(math.ceil(0.9 * n)) - 1)
    return ScoreDistribution(
        min_score=round(sorted_scores[0], 6),
        max_score=round(sorted_scores[-1], 6),
        mean_score=round(statistics.mean(sorted_scores), 6),
        p50_score=round(p50, 6),
        p90_score=round(sorted_scores[p90_idx], 6),
    )


# ── Hybrid Retriever ───────────────────────────────────────────────────────────

class HybridRetriever:
    """
    Production-grade hybrid retrieval that combines ChromaDB semantic search
    with BM25 keyword search, fused via Reciprocal Rank Fusion (RRF).

    **Full pipeline**:

    1. **Semantic search** — ChromaDB cosine similarity using query embeddings.
    2. **BM25 search** — Keyword relevance over all indexed chunk texts
       (index lazily built / rebuilt on demand).
    3. **RRF fusion** — ``score(d) = w_s/( K + rank_semantic ) + w_b/( K + rank_bm25 )``
       where ``w_s`` and ``w_b`` are configurable per-stream weights.
    4. **Top-K slice** — Return the top-K chunks by fused score (default 30).

    Downstream, these 30 chunks are passed to the :class:`~app.rag.reranker.Reranker`
    which applies a cross-encoder to reduce them to the final top-5.

    Usage::

        retriever = HybridRetriever()
        result = retriever.retrieve_with_metrics("What was Q3 revenue?", top_k=30)
        print(result.chunks)              # list[RetrievedChunk]
        print(result.num_vector_results)  # e.g. 30
        print(result.vector_search_latency_ms)
    """

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._bm25: BM25Okapi | None = None
        self._bm25_corpus: list[RetrievedChunk] = []
        logger.info("HybridRetriever initialised")

    # ── Public API ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Convenience wrapper — returns only the chunk list.

        Args:
            query: The user's search query.
            top_k: Number of fused results to return (default: ``settings.retrieval_top_k``).
            filter_document_ids: Restrict search to specific document UUIDs.

        Returns:
            List of :class:`~app.models.schemas.RetrievedChunk` sorted by
            descending RRF score, length ≤ *top_k*.
        """
        return self.retrieve_with_metrics(query, top_k=top_k, filter_document_ids=filter_document_ids).chunks

    def retrieve_with_metrics(
        self,
        query: str,
        top_k: int | None = None,
        filter_document_ids: list[str] | None = None,
    ) -> RetrievalResult:
        """
        Run the full hybrid retrieval pipeline and return both results and
        detailed observability metrics.

        Args:
            query: The user's search query.
            top_k: Number of results to return (default: ``settings.retrieval_top_k``).
            filter_document_ids: Restrict search to specific document UUIDs.

        Returns:
            :class:`RetrievalResult` containing the merged chunk list plus
            per-stage latencies and score distributions.
        """
        k = top_k or settings.retrieval_top_k
        result = RetrievalResult()
        pipeline_start = time.perf_counter()

        if self._vector_store.count() == 0:
            logger.warning("VectorStore is empty — returning no results.")
            return result

        # ── Stage 1: Semantic search ───────────────────────────────────────────
        t0 = time.perf_counter()
        semantic_chunks = self._semantic_search(query, top_k=k, filter_document_ids=filter_document_ids)
        result.vector_search_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.num_vector_results = len(semantic_chunks)

        if semantic_chunks:
            result.vector_score_dist = _compute_score_distribution(
                [c.semantic_score for c in semantic_chunks if c.semantic_score is not None]
            )

        # ── Stage 2: BM25 keyword search ───────────────────────────────────────
        t0 = time.perf_counter()
        keyword_chunks = self._bm25_search(query, top_k=k, filter_document_ids=filter_document_ids)
        result.bm25_search_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.num_bm25_results = len(keyword_chunks)

        if keyword_chunks:
            result.bm25_score_dist = _compute_score_distribution(
                [c.bm25_score for c in keyword_chunks if c.bm25_score is not None]
            )

        # ── Stage 3: Reciprocal Rank Fusion ────────────────────────────────────
        t0 = time.perf_counter()
        fused = self._reciprocal_rank_fusion(
            semantic_chunks,
            keyword_chunks,
            rrf_k=settings.rrf_k,
            semantic_weight=settings.semantic_weight,
            bm25_weight=settings.bm25_weight,
        )
        result.rrf_fusion_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        result.num_fused_results = len(fused)

        if fused:
            result.rrf_score_dist = _compute_score_distribution(
                [c.semantic_score for c in fused if c.semantic_score is not None]
            )

        # ── Stage 4: Slice to top-K ────────────────────────────────────────────
        result.chunks = fused[:k]
        result.total_retrieval_latency_ms = round(
            (time.perf_counter() - pipeline_start) * 1000, 2
        )

        logger.info(
            "Hybrid retrieval complete",
            extra={
                "query": query[:80],
                "top_k": k,
                "vector_hits": result.num_vector_results,
                "bm25_hits": result.num_bm25_results,
                "fused_total": result.num_fused_results,
                "returned": len(result.chunks),
                "vector_ms": result.vector_search_latency_ms,
                "bm25_ms": result.bm25_search_latency_ms,
                "rrf_ms": result.rrf_fusion_latency_ms,
                "total_ms": result.total_retrieval_latency_ms,
            },
        )
        return result

    def refresh_bm25_index(self) -> None:
        """
        Rebuild the in-memory BM25 index from all chunks currently in the
        vector store.  Must be called after new documents are indexed or
        deleted.
        """
        with log_latency(logger, "bm25_index_build"):
            raw = self._vector_store._collection.get(
                include=["documents", "metadatas"]
            )
            ids = raw.get("ids", [])
            docs = raw.get("documents", []) or []
            metas = raw.get("metadatas", []) or []

            if not docs:
                self._bm25 = None
                self._bm25_corpus = []
                return

            tokenised = [text.lower().split() for text in docs]
            self._bm25 = BM25Okapi(tokenised)

            from app.models.schemas import ChunkMetadata  # local avoids circular

            self._bm25_corpus = []
            for cid, text, meta in zip(ids, docs, metas):
                page_val = meta.get("page")
                try:
                    page_num = int(page_val) if page_val and str(page_val).isdigit() else None
                except (ValueError, TypeError):
                    page_num = None

                chunk_meta = ChunkMetadata(
                    source=meta.get("source", "unknown"),
                    document_name=meta.get("document_name") or meta.get("source") or "unknown",
                    page=page_num,
                    file_type=meta.get("file_type") or "",
                    chunk_id=cid,
                    document_id=meta.get("document_id", ""),
                )
                self._bm25_corpus.append(
                    RetrievedChunk(
                        chunk_id=cid,
                        content=text,
                        metadata=chunk_meta,
                    )
                )

        logger.info(
            "BM25 index rebuilt",
            extra={"corpus_size": len(self._bm25_corpus)},
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _semantic_search(
        self,
        query: str,
        top_k: int,
        filter_document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Delegate to ChromaDB for vector-space similarity search."""
        with log_latency(logger, "vector_store_search", query_length=len(query), top_k=top_k):
            try:
                return self._vector_store.search(
                    query, top_k=top_k, filter_document_ids=filter_document_ids
                )
            except Exception as exc:
                logger.error("Semantic search failed", extra={"error": str(exc)})
                return []

    def _bm25_search(
        self,
        query: str,
        top_k: int,
        filter_document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Run BM25 keyword search.  Lazily builds the index on the first call.
        """
        if self._bm25 is None or not self._bm25_corpus:
            self.refresh_bm25_index()

        if self._bm25 is None or not self._bm25_corpus:
            return []

        tokenised_query = query.lower().split()
        try:
            scores = self._bm25.get_scores(tokenised_query)
        except Exception as exc:
            logger.error("BM25 scoring failed", extra={"error": str(exc)})
            return []

        # Sort by descending score and attach BM25 scores to chunk copies
        scored_pairs = sorted(
            zip(scores, self._bm25_corpus), key=lambda x: x[0], reverse=True
        )

        # Apply document filter if provided
        if filter_document_ids:
            filter_set = set(filter_document_ids)
            scored_pairs = [
                (score, chunk) for score, chunk in scored_pairs
                if chunk.metadata.document_id in filter_set
            ]

        results: list[RetrievedChunk] = []
        for score, chunk in scored_pairs[:top_k]:
            # Clone to avoid mutating the corpus index
            chunk_copy = chunk.model_copy(deep=True)
            chunk_copy.bm25_score = round(float(score), 6)
            results.append(chunk_copy)

        return results

    @staticmethod
    def _reciprocal_rank_fusion(
        semantic_chunks: list[RetrievedChunk],
        bm25_chunks: list[RetrievedChunk],
        rrf_k: int = 60,
        semantic_weight: float = 1.0,
        bm25_weight: float = 1.0,
    ) -> list[RetrievedChunk]:
        """
        Merge semantic and BM25 ranked lists using weighted Reciprocal Rank Fusion.

        Formula for document *d*:

            ``rrf_score(d) = w_s/(K + rank_semantic(d)) + w_b/(K + rank_bm25(d))``

        Unranked documents (present in only one list) still receive a contribution
        from the list they appear in.

        Args:
            semantic_chunks:  Ordered list of chunks from vector search.
            bm25_chunks:      Ordered list of chunks from BM25 search.
            rrf_k:            RRF constant K (default 60, per Cormack et al. 2009).
            semantic_weight:  Multiplicative weight applied to semantic scores.
            bm25_weight:      Multiplicative weight applied to BM25 scores.

        Returns:
            De-duplicated list of :class:`~app.models.schemas.RetrievedChunk` sorted
            by descending fused RRF score.  ``chunk.semantic_score`` is set to the
            final RRF score for downstream display.
        """
        rrf_scores: dict[str, float] = defaultdict(float)
        chunk_by_id: dict[str, RetrievedChunk] = {}

        # Semantic stream
        for rank, chunk in enumerate(semantic_chunks, start=1):
            rrf_scores[chunk.chunk_id] += semantic_weight / (rrf_k + rank)
            if chunk.chunk_id not in chunk_by_id:
                chunk_by_id[chunk.chunk_id] = chunk

        # BM25 stream
        for rank, chunk in enumerate(bm25_chunks, start=1):
            rrf_scores[chunk.chunk_id] += bm25_weight / (rrf_k + rank)
            if chunk.chunk_id not in chunk_by_id:
                chunk_by_id[chunk.chunk_id] = chunk

        # Sort by descending RRF score
        sorted_ids = sorted(
            rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True
        )

        fused: list[RetrievedChunk] = []
        for cid in sorted_ids:
            chunk = chunk_by_id[cid]
            chunk.semantic_score = round(rrf_scores[cid], 6)
            fused.append(chunk)

        return fused


# ── Module-level singleton ─────────────────────────────────────────────────────

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """
    Return the singleton :class:`HybridRetriever` instance.
    """
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
