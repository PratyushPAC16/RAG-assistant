"""
Enterprise Agentic RAG Assistant
RAG Agent — orchestrates hybrid retrieval, reranking, prompt assembly,
and Gemini answer generation with source citations.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.llm_factory import get_llm

from app.models.schemas import (
    AgentState,
    AgentType,
    RetrievedChunk,
    SourceCitation,
)
from app.rag.retriever import HybridRetriever, get_retriever
from app.rag.reranker import Reranker, get_reranker
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()

# ── System prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert Enterprise Knowledge Assistant with access to a curated document corpus.

Your responsibilities:
1. Provide accurate, well-structured answers based ONLY on the provided context.
2. Always cite your sources using [Source: <filename>, Page <N>] notation inline.
3. If the context does not contain sufficient information to answer the question, clearly state this.
4. Structure complex answers with headers and bullet points for readability.
5. Be concise but comprehensive — avoid padding or repetition.
6. Maintain a professional and authoritative tone.

Important: Do NOT fabricate information beyond what is explicitly in the provided context."""

_ANSWER_PROMPT_TEMPLATE = """CONTEXT FROM DOCUMENTS:
{context}

CONVERSATION HISTORY:
{history}

USER QUESTION:
{query}

INSTRUCTIONS:
- Answer based solely on the context above.
- Cite sources inline as [Source: <filename>, Page <N>].
- If context is insufficient, say "The documents do not contain enough information to answer this question."

ANSWER:"""


class RAGAgent:
    """
    Retrieval-Augmented Generation agent.

    Pipeline:
    1. Receive query from :class:`~app.models.schemas.AgentState`.
    2. Run hybrid retrieval (semantic + BM25).
    3. Rerank retrieved chunks with a cross-encoder.
    4. Assemble context string from top-K chunks.
    5. Generate answer via Gemini.
    6. Extract and return source citations.
    """

    def __init__(
        self,
        retriever: HybridRetriever | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self._retriever = retriever or get_retriever()
        self._reranker = reranker or get_reranker()
        self._llm = get_llm(
            temperature=settings.gemini_temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        logger.info(
            "RAGAgent initialised",
            extra={"llm_provider": settings.llm_provider},
        )

    # ── LangGraph node entry-point ─────────────────────────────────────────────

    def run(self, state: AgentState) -> AgentState:
        """
        Execute the retrieval and reranking pipeline and update the agent state.

        Args:
            state: Current :class:`~app.models.schemas.AgentState`.

        Returns:
            Updated state with ``retrieved_chunks`` and ``reranked_chunks`` populated.
        """
        query = state.query
        logger.info("RAGAgent.run called", extra={"query": query[:80]})

        try:
            # ── Step 1: Hybrid retrieval with detailed metrics ─────────────────
            retrieval_result = self._retriever.retrieve_with_metrics(
                query=query,
                top_k=settings.retrieval_top_k,
                filter_document_ids=state.filter_document_ids,
            )
            chunks = retrieval_result.chunks
            state.retrieved_chunks = chunks

            # Emit per-stage latency into state for analytics
            state.latency_ms["retrieval"] = retrieval_result.total_retrieval_latency_ms
            state.latency_ms["vector_search"] = retrieval_result.vector_search_latency_ms
            state.latency_ms["bm25_search"] = retrieval_result.bm25_search_latency_ms
            state.latency_ms["rrf_fusion"] = retrieval_result.rrf_fusion_latency_ms

            # Store extended retrieval stats for analytics API
            state.latency_ms["num_vector_results"] = float(retrieval_result.num_vector_results)
            state.latency_ms["num_bm25_results"] = float(retrieval_result.num_bm25_results)

            if not chunks:
                state.reranked_chunks = []
                if state.agent_type != AgentType.HYBRID:
                    state.agent_type = AgentType.RAG
                return state

            # ── Step 2: Cross-encoder reranking ────────────────────────────────
            with log_latency(logger, "rag_reranking") as rerank_ctx:
                reranked = self._reranker.rerank(
                    query=query,
                    chunks=chunks,
                    top_k=settings.reranker_top_k,
                )
            state.reranked_chunks = reranked
            state.latency_ms["reranking"] = rerank_ctx.get("latency_ms", 0.0)
            if state.agent_type != AgentType.HYBRID:
                state.agent_type = AgentType.RAG

        except Exception as exc:
            error_str = str(exc)
            logger.error(
                "RAGAgent.run failed",
                extra={"error": error_str, "query": query[:80]},
                exc_info=True,
            )
            state.error = error_str

        return state

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        """
        Assemble a structured context string from reranked chunks.
        Each chunk is prefixed with its source and page for inline citation.
        """
        parts: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            meta = chunk.metadata
            header = f"[{i}] Source: {meta.source}"
            if meta.page:
                header += f", Page {meta.page}"
            parts.append(f"{header}\n{chunk.content}")
        return "\n\n---\n\n".join(parts)

    def _format_history(self, state: AgentState) -> str:
        """Format conversation history as a plain-text block."""
        if not state.conversation_history:
            return "No previous conversation."
        lines = []
        for msg in state.conversation_history[-6:]:  # Last 3 turns
            lines.append(f"{msg.role.value.capitalize()}: {msg.content}")
        return "\n".join(lines)

    def _generate_answer(
        self, query: str, context: str, history: str
    ) -> str:
        """
        Call Gemini to generate the final answer given context and history.

        Args:
            query:   The user's question.
            context: Assembled chunk context.
            history: Formatted conversation history.

        Returns:
            The generated answer string.
        """
        prompt = _ANSWER_PROMPT_TEMPLATE.format(
            context=context, history=history, query=query
        )
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = self._llm.invoke(messages)
        return response.content

    @staticmethod
    def _extract_citations(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
        """
        Build deduplicated source citations from the reranked chunks.
        Preserves order by first appearance (best-ranked chunk per source).
        """
        seen: set[tuple[str, int | None]] = set()
        citations: list[SourceCitation] = []
        for chunk in chunks:
            key = (chunk.metadata.source, chunk.metadata.page)
            if key not in seen:
                seen.add(key)
                citations.append(
                    SourceCitation(
                        document=chunk.metadata.source,
                        page=chunk.metadata.page,
                        chunk_id=chunk.chunk_id,
                        relevance_score=chunk.rerank_score,
                        text=chunk.text,
                    )
                )
        return citations


# ── Module-level singleton ─────────────────────────────────────────────────────

_rag_agent: RAGAgent | None = None


def get_rag_agent() -> RAGAgent:
    """Return the singleton RAGAgent instance."""
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent
