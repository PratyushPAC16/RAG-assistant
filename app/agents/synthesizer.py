"""
Enterprise Agentic RAG Assistant
Response Synthesizer Agent — combines context from documents, web results,
and conversation memory to generate a cohesive answer with source citations.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.schemas import AgentState, RetrievedChunk, SourceCitation
from app.utils.config import get_settings
from app.utils.llm_factory import get_llm
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()

_SYNTHESIS_SYSTEM_PROMPT = """You are an expert Enterprise Knowledge Synthesizer.
Your goal is to provide a comprehensive, accurate, and professional answer to the user's query.

CRITICAL CITATION RULES:
1. For any information based on UPLOADED DOCUMENTS, you MUST cite the source filename and page using: [Source: <filename>, Page <N>].
   - If page number is not available, use [Source: <filename>].
   - Example: "The company's Q3 revenue was $15M [Source: Q3_Report.pdf, Page 4]."
2. For any information based on WEB SEARCH RESULTS, you MUST cite the source URL using: [Source: <URL>].
   - Example: "OpenAI announced GPT-5 in June 2026 [Source: https://openai.com/blog/gpt-5]."
3. For any information based on previous turns in the CONVERSATION HISTORY, you MUST cite using: [Turn <N>].
   - Example: "As explained earlier [Turn 2], the main risk is inflation."
4. If the provided context is insufficient or does not contain the answer, state that clearly. Do NOT fabricate or make up any information.
5. Format your response clearly using markdown headers, bullet points, and bold text where appropriate.
"""

_SYNTHESIS_PROMPT_TEMPLATE = """USER QUERY:
{query}

CONTEXT PROVIDED:
{context_block}

CONVERSATION HISTORY:
{history_block}

INSTRUCTIONS:
- Answer the user query using the provided context and history.
- Apply the inline citation rules strictly.
- Synthesize information from both documents and web results if both are present.

ANSWER:"""


class ResponseSynthesizer:
    """
    Unified agent responsible for generating the final citation-grounded response.
    Can synthesize answers for RAG, Web Search, Memory, and Hybrid workflows.
    """

    def __init__(self) -> None:
        self._llm = get_llm(
            temperature=settings.gemini_temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        logger.info(
            "ResponseSynthesizer initialised",
            extra={"llm_provider": settings.llm_provider},
        )

    def run(self, state: AgentState) -> AgentState:
        """
        Execute the synthesis process on the current agent state.
        """
        query = state.query
        logger.info("ResponseSynthesizer.run called", extra={"query": query[:80]})

        try:
            # ── 1. Build context block ─────────────────────────────────────────
            context_parts = []

            # Document chunks
            if getattr(state, "retrieved_memories", None):
                mem_context = []
                for mem in state.retrieved_memories:
                    m_type = getattr(mem, "memory_type", "") or (mem.get("memory_type", "") if isinstance(mem, dict) else "")
                    m_content = getattr(mem, "content", "") or (mem.get("content", "") if isinstance(mem, dict) else "")
                    if not m_type and not isinstance(mem, dict):
                        m_type = mem.memory_type
                        m_content = mem.content
                    mem_context.append(f"- [{m_type.upper()}] {m_content}")
                context_parts.append("### RELEVANT LONG-TERM USER MEMORIES & PREFERENCES:\n" + "\n".join(mem_context))

            if state.reranked_chunks:
                doc_context = []
                for i, chunk in enumerate(state.reranked_chunks, start=1):
                    meta = chunk.metadata
                    header = f"Document Chunk {i} - Source: {meta.source}"
                    if meta.page:
                        header += f", Page {meta.page}"
                    doc_context.append(f"{header}\nContent: {chunk.content}")
                context_parts.append("### UPLOADED DOCUMENTS:\n" + "\n\n".join(doc_context))

            # Web results
            if state.web_results:
                web_context = []
                for i, res in enumerate(state.web_results, start=1):
                    title = res.get("title", "Web Source")
                    url = res.get("url", "")
                    content = res.get("content", "")
                    web_context.append(f"Web Source {i} - Title: {title}\nURL: {url}\nContent: {content}")
                context_parts.append("### WEB SEARCH RESULTS:\n" + "\n\n".join(web_context))

            context_block = "\n\n---\n\n".join(context_parts) if context_parts else "No document or web search context available."

            # ── 2. Build history block ─────────────────────────────────────────
            history_block = self._format_history(state)

            # ── 3. Run LLM synthesis ───────────────────────────────────────────
            prompt = _SYNTHESIS_PROMPT_TEMPLATE.format(
                query=query,
                context_block=context_block,
                history_block=history_block,
            )

            messages = [
                SystemMessage(content=_SYNTHESIS_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]

            with log_latency(logger, "synthesis_llm_generation") as llm_ctx:
                response = self._llm.invoke(messages)
                answer = response.content
                
                from app.utils.llm_factory import extract_token_usage, calculate_cost
                p_tok, c_tok, t_tok = extract_token_usage(response)
                state.prompt_tokens += p_tok
                state.completion_tokens += c_tok
                state.total_tokens += t_tok
                state.cost_usd += calculate_cost(p_tok, c_tok)
            state.latency_ms["synthesis_llm"] = llm_ctx.get("latency_ms", 0.0)

            # ── 4. Extract citations and update state ──────────────────────────
            state.answer = answer
            state.sources = self._extract_citations(answer, state.reranked_chunks, state.web_results)

        except Exception as exc:
            error_str = str(exc)
            logger.error(
                "ResponseSynthesizer failed",
                extra={"error": error_str, "query": query[:80]},
                exc_info=True,
            )
            state.error = error_str
            state.answer = f"Error during synthesis: {error_str}"

        return state

    def _format_history(self, state: AgentState) -> str:
        """Format conversation history for LLM prompt."""
        if not state.conversation_history:
            return "No previous conversation."
        lines = []
        for i, msg in enumerate(state.conversation_history[-6:], start=1):
            role_label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"[Turn {i}] {role_label}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _extract_citations(
        answer: str, chunks: list[RetrievedChunk], web_results: list[dict[str, Any]]
    ) -> list[SourceCitation]:
        """
        Parse final answer and construct a list of active SourceCitation objects.
        """
        citations: list[SourceCitation] = []
        seen: set[tuple[str, int | None] | str] = set()

        # 1. Document citations: [Source: <filename>, Page <N>] or [Source: <filename>]
        doc_matches = re.findall(r"\[Source:\s*([^,\]]+)(?:,\s*Page\s*(\d+))?\]", answer, re.IGNORECASE)
        for doc_name, page_str in doc_matches:
            doc_name = doc_name.strip()
            if doc_name.lower().startswith("http://") or doc_name.lower().startswith("https://"):
                continue
            page = int(page_str) if page_str else None
            key = (doc_name, page)
            if key not in seen:
                # Find matching chunk metadata
                matched_chunk = None
                for chunk in chunks:
                    if chunk.metadata.source.lower() == doc_name.lower():
                        if page is None or chunk.metadata.page == page:
                            matched_chunk = chunk
                            break
                if matched_chunk:
                    seen.add(key)
                    citations.append(
                        SourceCitation(
                            document=matched_chunk.metadata.source,
                            page=matched_chunk.metadata.page,
                            chunk_id=matched_chunk.chunk_id,
                            relevance_score=matched_chunk.rerank_score or 1.0,
                        )
                    )
                else:
                    seen.add(key)
                    citations.append(
                        SourceCitation(
                            document=doc_name,
                            page=page,
                            relevance_score=0.5,
                        )
                    )

        # 2. Web search citations: [Source: <URL>]
        web_matches = re.findall(r"\[Source:\s*(https?://[^\s\]]+)\]", answer, re.IGNORECASE)
        for url in web_matches:
            url = url.strip()
            if url not in seen:
                seen.add(url)
                # Find corresponding website title
                title = "Web Link"
                for res in web_results:
                    if res.get("url") == url:
                        title = res.get("title", title)
                        break
                citations.append(
                    SourceCitation(
                        document=title,
                        page=None,
                        chunk_id=url,
                        relevance_score=1.0,
                    )
                )

        return citations


# ── Module-level singleton ─────────────────────────────────────────────────────

_synthesizer: ResponseSynthesizer | None = None


def get_synthesizer() -> ResponseSynthesizer:
    """Return the singleton ResponseSynthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = ResponseSynthesizer()
    return _synthesizer
