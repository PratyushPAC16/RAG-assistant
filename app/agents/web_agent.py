"""
Enterprise Agentic RAG Assistant
Web Search Agent — uses Tavily to search the internet, summarise results,
and return structured citations for current-events queries.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from tavily import TavilyClient

from app.models.schemas import (
    AgentState,
    AgentType,
    SourceCitation,
)
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency
from app.utils.llm_factory import get_llm

logger = get_logger(__name__)
settings = get_settings()

_SUMMARISE_SYSTEM_PROMPT = """You are an expert research assistant that synthesises web search results into clear, accurate answers.

Guidelines:
1. Synthesise information from multiple sources into a coherent answer.
2. Cite sources inline using [Source: <URL>] notation.
3. Prioritise recent information and authoritative sources.
4. Be objective and fact-based.
5. Flag any conflicting information across sources.
6. Clearly indicate when information may be outdated."""

_SUMMARISE_PROMPT_TEMPLATE = """WEB SEARCH RESULTS FOR: "{query}"

{results}

CONVERSATION HISTORY:
{history}

Synthesise the above search results into a comprehensive, well-cited answer.
Use [Source: <URL>] citations inline. If the results don't fully answer the question,
acknowledge the limitation."""


class WebSearchAgent:
    """
    Agent that searches the internet via Tavily and uses Gemini to summarise
    the results into a coherent, cited answer.

    Usage (via LangGraph)::

        web_agent = WebSearchAgent()
        updated_state = web_agent.run(state)
    """

    def __init__(self) -> None:
        self._tavily = TavilyClient(api_key=settings.tavily_api_key)
        self._llm = get_llm(
            temperature=settings.gemini_temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        logger.info(
            "WebSearchAgent initialised",
            extra={"llm_provider": settings.llm_provider},
        )

    # ── LangGraph node entry-point ─────────────────────────────────────────────

    def run(self, state: AgentState) -> AgentState:
        """
        Execute the web search pipeline and update agent state.

        Args:
            state: Current :class:`~app.models.schemas.AgentState`.

        Returns:
            Updated state with ``web_results`` and ``agent_type`` set.
        """
        query = state.query
        logger.info("WebSearchAgent.run called", extra={"query": query[:80]})

        try:
            # ── Step 1: Tavily web search ──────────────────────────────────────
            with log_latency(logger, "web_search", query=query) as search_ctx:
                raw_results = self._search(query)
            state.web_results = raw_results
            state.latency_ms["web_search"] = search_ctx.get("latency_ms", 0.0)
            state.agent_type = AgentType.WEB

        except Exception as exc:
            logger.error(
                "WebSearchAgent.run failed",
                extra={"error": str(exc), "query": query[:80]},
                exc_info=True,
            )
            state.error = str(exc)

        return state

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _search(self, query: str, max_results: int = 8) -> list[dict[str, Any]]:
        """
        Call Tavily search API and return structured results.

        Args:
            query:       The search query.
            max_results: Maximum number of results to fetch.

        Returns:
            List of result dicts with keys: url, title, content, score.
        """
        try:
            response = self._tavily.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=False,
                include_raw_content=False,
            )
            results: list[dict[str, Any]] = response.get("results", [])
            logger.debug(
                "Tavily search complete",
                extra={"num_results": len(results)},
            )
            return results
        except Exception as exc:
            logger.error("Tavily search failed", extra={"error": str(exc)})
            raise

    def _format_results(self, results: list[dict[str, Any]]) -> str:
        """
        Format raw Tavily results into a prompt-ready string.
        """
        parts: list[str] = []
        for i, result in enumerate(results, start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            content = result.get("content", "").strip()
            parts.append(
                f"[Result {i}]\nTitle: {title}\nURL: {url}\nContent: {content}"
            )
        return "\n\n---\n\n".join(parts)

    def _summarise(self, query: str, formatted_results: str, history: str) -> str:
        """
        Use Gemini to synthesise search results into a coherent answer.
        """
        prompt = _SUMMARISE_PROMPT_TEMPLATE.format(
            query=query,
            results=formatted_results,
            history=history,
        )
        messages = [
            SystemMessage(content=_SUMMARISE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = self._llm.invoke(messages)
        return response.content

    @staticmethod
    def _format_history(state: AgentState) -> str:
        """Format conversation history."""
        if not state.conversation_history:
            return "No previous conversation."
        lines = []
        for msg in state.conversation_history[-6:]:
            lines.append(f"{msg.role.value.capitalize()}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _build_citations(results: list[dict[str, Any]]) -> list[SourceCitation]:
        """
        Build SourceCitation objects from web results.
        Uses URL as the document identifier.
        """
        citations: list[SourceCitation] = []
        for result in results:
            url = result.get("url", "")
            if url:
                citations.append(
                    SourceCitation(
                        document=result.get("title", url),
                        page=None,  # Web results don't have pages
                        chunk_id=None,
                        relevance_score=result.get("score"),
                    )
                )
        return citations


# ── Module-level singleton ─────────────────────────────────────────────────────

_web_agent: WebSearchAgent | None = None


def get_web_agent() -> WebSearchAgent:
    """Return the singleton WebSearchAgent instance."""
    global _web_agent
    if _web_agent is None:
        _web_agent = WebSearchAgent()
    return _web_agent
