"""
Enterprise Agentic RAG Assistant
Hybrid retrieval pipeline — fuses semantic search (ChromaDB) with
keyword search (BM25) using Reciprocal Rank Fusion (RRF).

Returns the top-K most relevant chunks for a query.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Sequence

from rank_bm25 import BM25Okapi

from app.models.schemas import RetrievedChunk
from app.rag.vector_store import VectorStore, get_vector_store
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()

# RRF constant — standard value from the original paper (Cormack et al., 2009)
_RRF_K = 60


class HybridRetriever:
    """
    Combines ChromaDB semantic retrieval with BM25 keyword retrieval using
    Reciprocal Rank Fusion to produce a unified ranked list.

    **Retrieval Pipeline**:

    1. Semantic search via ChromaDB (cosine similarity on Gemini embeddings).
    2. BM25 keyword search over all indexed chunk texts.
    3. RRF score fusion: ``rrf(r) = 1 / (K + r)`` summed across both rankings.
    4. Return the top-*N* chunks by fused score.

    Usage::

        retriever = HybridRetriever()
        chunks = retriever.retrieve("What was the Q3 revenue?", top_k=20)
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
    ) -> list[RetrievedChunk]:
        """
        Run the full hybrid retrieval pipeline.

        Args:
            query: The user's search query.
            top_k: Number of results to return (default: ``settings.retrieval_top_k``).

        Returns:
            List of :class:`~app.models.schemas.RetrievedChunk` objects sorted by
            descending fused relevance score, length ≤ *top_k*.
        """
        k = top_k or settings.retrieval_top_k

        if self._vector_store.count() == 0:
            logger.warning("VectorStore is empty — returning no results.")
            return []

        with log_latency(logger, "hybrid_retrieval", query=query, top_k=k):
            # ── Step 1: Semantic search ────────────────────────────────────────
            semantic_chunks = self._semantic_search(query, top_k=k)

            # ── Step 2: BM25 keyword search ───────────────────────────────────
            keyword_chunks = self._bm25_search(query, top_k=k)

            # ── Step 3: Reciprocal Rank Fusion ────────────────────────────────
            fused = self._reciprocal_rank_fusion(semantic_chunks, keyword_chunks)

            # ── Step 4: Take top-K ────────────────────────────────────────────
            results = fused[:k]

        logger.info(
            "Hybrid retrieval complete",
            extra={
                "query": query[:80],
                "semantic_hits": len(semantic_chunks),
                "bm25_hits": len(keyword_chunks),
                "returned": len(results),
            },
        )
        return results

    def refresh_bm25_index(self) -> None:
        """
        Rebuild the in-memory BM25 index from all chunks currently in the vector
        store.  Must be called after new documents are indexed.
        """
        with log_latency(logger, "bm25_index_build"):
            all_metas = self._vector_store.get_all_documents_metadata()
            if not all_metas:
                self._bm25 = None
                self._bm25_corpus = []
                return

            # We need the raw texts; query ChromaDB for everything
            raw = self._vector_store._collection.get(
                include=["documents", "metadatas"]
            )
            ids = raw.get("ids", [])
            docs = raw.get("documents", []) or []
            metas = raw.get("metadatas", []) or []

            tokenised = [text.lower().split() for text in docs]
            self._bm25 = BM25Okapi(tokenised)

            # Build lightweight RetrievedChunk stubs for BM25 results
            from app.models.schemas import ChunkMetadata  # local import avoids cycles

            self._bm25_corpus = []
            for cid, text, meta in zip(ids, docs, metas):
                page_val = meta.get("page")
                try:
                    page_num = int(page_val) if page_val and str(page_val).isdigit() else None
                except (ValueError, TypeError):
                    page_num = None

                chunk_meta = ChunkMetadata(
                    source=meta.get("source", "unknown"),
                    page=page_num,
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

    def _semantic_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        """Delegate to ChromaDB for vector-space similarity search."""
        try:
            return self._vector_store.search(query, top_k=top_k)
        except Exception as exc:
            logger.error("Semantic search failed", extra={"error": str(exc)})
            return []

    def _bm25_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
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

        # Sort by descending score and attach BM25 scores to chunks
        scored_pairs = sorted(
            zip(scores, self._bm25_corpus), key=lambda x: x[0], reverse=True
        )
        results: list[RetrievedChunk] = []
        for score, chunk in scored_pairs[:top_k]:
            chunk.bm25_score = round(float(score), 6)
            results.append(chunk)

        return results

    @staticmethod
    def _reciprocal_rank_fusion(
        *ranked_lists: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        Merge multiple ranked lists using Reciprocal Rank Fusion.

        RRF score for a document ``d`` across lists ``L₁…Lₙ``:
            ``score(d) = Σ 1 / (K + rank_in_Lᵢ(d))``

        Args:
            *ranked_lists: One or more ordered lists of RetrievedChunk.

        Returns:
            De-duplicated list of RetrievedChunk sorted by descending RRF score,
            with ``semantic_score`` updated to the fused value.
        """
        rrf_scores: dict[str, float] = defaultdict(float)
        chunk_by_id: dict[str, RetrievedChunk] = {}

        for ranked in ranked_lists:
            for rank, chunk in enumerate(ranked, start=1):
                rrf_scores[chunk.chunk_id] += 1.0 / (_RRF_K + rank)
                if chunk.chunk_id not in chunk_by_id:
                    chunk_by_id[chunk.chunk_id] = chunk

        # Sort by descending RRF score
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

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
