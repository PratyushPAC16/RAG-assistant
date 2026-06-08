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
        Execute the RAG pipeline and update the agent state.

        This method is designed to be used as a LangGraph node:
        it accepts a state dict-like object and returns an updated state.

        Args:
            state: Current :class:`~app.models.schemas.AgentState`.

        Returns:
            Updated state with ``answer``, ``sources``, ``retrieved_chunks``,
            ``reranked_chunks``, ``context``, and ``agent_type`` populated.
        """
        query = state.query
        logger.info("RAGAgent.run called", extra={"query": query[:80]})

        try:
            # ── Step 1: Hybrid retrieval ───────────────────────────────────────
            with log_latency(logger, "rag_retrieval") as retrieval_ctx:
                chunks = self._retriever.retrieve(
                    query=query, top_k=settings.retrieval_top_k
                )
            state.retrieved_chunks = chunks
            state.latency_ms["retrieval"] = retrieval_ctx.get("latency_ms", 0.0)

            if not chunks:
                state.answer = (
                    "No relevant documents were found in the knowledge base. "
                    "Please upload documents first or rephrase your query."
                )
                state.sources = []
                state.agent_type = AgentType.RAG
                return state

            # ── Step 2: Reranking ──────────────────────────────────────────────
            with log_latency(logger, "rag_reranking") as rerank_ctx:
                reranked = self._reranker.rerank(
                    query=query,
                    chunks=chunks,
                    top_k=settings.reranker_top_k,
                )
            state.reranked_chunks = reranked
            state.latency_ms["reranking"] = rerank_ctx.get("latency_ms", 0.0)

            # ── Step 3: Context assembly ───────────────────────────────────────
            context = self._build_context(reranked)
            state.context = context

            # ── Step 4: Conversation history ───────────────────────────────────
            history = self._format_history(state)

            # ── Step 5: LLM generation ─────────────────────────────────────────
            with log_latency(logger, "rag_llm_generation") as llm_ctx:
                answer = self._generate_answer(query, context, history)
            state.latency_ms["llm"] = llm_ctx.get("latency_ms", 0.0)

            # ── Step 6: Citations ──────────────────────────────────────────────
            state.answer = answer
            state.sources = self._extract_citations(reranked)
            state.agent_type = AgentType.RAG

        except Exception as exc:
            error_str = str(exc)
            logger.error(
                "RAGAgent.run failed",
                extra={"error": error_str, "query": query[:80]},
                exc_info=True,
            )
            state.error = error_str

            # ── Friendly quota / rate-limit messages ───────────────────────────
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                if "limit: 0" in error_str or "free_tier" in error_str:
                    state.answer = (
                        "🚫 **Google API Quota Exhausted**\n\n"
                        "Your Google Cloud project's free-tier quota for this model has reached its **limit of 0**.\n\n"
                        "**To fix this:**\n"
                        "1. Go to [Google AI Studio](https://aistudio.google.com) and create a **new project** with a fresh API key.\n"
                        "2. Or enable **billing** on your current Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com).\n"
                        "3. Update `GOOGLE_API_KEY` in your `.env` file, then restart the server.\n\n"
                        "_Note: Getting a new key from the same exhausted project will not help — you need a new project or billing enabled._"
                    )
                else:
                    # Temporary rate limit — may have a retry-after hint
                    retry_match = re.search(r"retry in ([\d.]+)s", error_str, re.IGNORECASE)
                    retry_hint = f" Please wait **{retry_match.group(1)} seconds** and try again." if retry_match else " Please try again in a few minutes."
                    state.answer = (
                        f"⏳ **Rate Limit Reached**\n\n"
                        f"The Google Gemini API has temporarily rate-limited your requests.{retry_hint}\n\n"
                        "If this keeps happening, consider switching to a paid API tier."
                    )
            else:
                state.answer = (
                    f"An error occurred while processing your query: {exc}\n"
                    "Please try again or contact support."
                )

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
