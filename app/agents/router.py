"""
Enterprise Agentic RAG Assistant
Router Agent — classifies incoming queries and routes them to the appropriate
agent: RAG, Web Search, or Memory.

Uses Gemini as the classification LLM with a structured JSON output.
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.schemas import AgentState, AgentType
from app.rag.vector_store import VectorStore, get_vector_store
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency
from app.utils.llm_factory import get_llm

logger = get_logger(__name__)
settings = get_settings()

# ── Router prompt ──────────────────────────────────────────────────────────────
_ROUTER_SYSTEM_PROMPT = """You are an intelligent query routing system for an Enterprise RAG Assistant.

Your task is to classify the user's query and route it to the most appropriate agent.

Available agents:
1. "rag"    — For questions about uploaded documents, knowledge base, reports, data, PDFs.
2. "web"    — For questions requiring current/real-time information, news, recent events, prices, or facts not in documents.
3. "memory" — For follow-up questions, clarifications about previous answers, or references to "earlier", "before", "last time", etc.

Decision rules:
- If the query references "the document", "the report", "the file", "in the data" → "rag"
- If the query asks about "latest", "current", "today", "news", "recent" → "web"
- If the query uses "you said", "earlier", "before", "the previous answer", "continue" → "memory"
- If the vector store is empty (no documents indexed), prefer "web" over "rag"
- Default to "rag" when uncertain and documents are available

Respond ONLY with a JSON object in this exact format:
{
  "agent": "<rag|web|memory>",
  "reasoning": "<one sentence explaining the routing decision>",
  "confidence": <0.0-1.0>
}"""

_ROUTER_PROMPT_TEMPLATE = """USER QUERY: {query}

CONTEXT:
- Documents indexed in knowledge base: {num_docs}
- Has conversation history: {has_history}
- History preview: {history_preview}

Route this query to the most appropriate agent."""


class RouterAgent:
    """
    Intelligent query router that uses Gemini to classify queries and
    dispatch them to the correct downstream agent.

    The router considers:
    1. Query intent (document, web, memory).
    2. Whether the vector store has indexed documents.
    3. Whether there is active conversation history.

    When classification confidence is low, it defaults to RAG (if documents
    exist) or WEB (if the knowledge base is empty).
    """

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self._vector_store = vector_store or get_vector_store()
        self._llm = get_llm(
            temperature=0.0,  # Deterministic routing
            max_output_tokens=256,
        )
        logger.info(
            "RouterAgent initialised",
            extra={"llm_provider": settings.llm_provider},
        )

    # ── LangGraph node entry-point ─────────────────────────────────────────────

    def route(self, state: AgentState) -> AgentState:
        """
        Classify the query and set ``state.agent_type``.

        This node does NOT call the downstream agents — it only sets the routing
        decision.  LangGraph uses the returned agent_type to select the next node.

        Args:
            state: Current :class:`~app.models.schemas.AgentState`.

        Returns:
            State with ``agent_type`` set.
        """
        query = state.query
        logger.info("RouterAgent.route called", extra={"query": query[:80]})

        try:
            num_docs = self._vector_store.count()
            has_history = bool(state.conversation_history)
            history_preview = self._preview_history(state)

            with log_latency(logger, "routing", query=query) as route_ctx:
                agent_type = self._classify(
                    query=query,
                    num_docs=num_docs,
                    has_history=has_history,
                    history_preview=history_preview,
                )
            state.latency_ms["routing"] = route_ctx.get("latency_ms", 0.0)

            state.agent_type = agent_type
            logger.info(
                "Query routed",
                extra={"query": query[:80], "agent": agent_type.value},
            )

        except Exception as exc:
            logger.error(
                "RouterAgent.route failed — defaulting to RAG",
                extra={"error": str(exc)},
                exc_info=True,
            )
            state.agent_type = AgentType.RAG

        return state

    def get_next_node(self, state: AgentState) -> str:
        """
        LangGraph conditional edge function.
        Returns the name of the next node based on state.agent_type.

        Args:
            state: Current state with ``agent_type`` set by :meth:`route`.

        Returns:
            Node name string: ``"rag_node"``, ``"web_node"``, or ``"memory_node"``.
        """
        mapping = {
            AgentType.RAG: "rag_node",
            AgentType.WEB: "web_node",
            AgentType.MEMORY: "memory_node",
        }
        agent = state.agent_type or AgentType.RAG
        return mapping.get(agent, "rag_node")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _classify(
        self,
        query: str,
        num_docs: int,
        has_history: bool,
        history_preview: str,
    ) -> AgentType:
        """
        Use Gemini to classify the query as rag / web / memory.
        Falls back to rule-based routing if LLM output cannot be parsed.
        """
        prompt = _ROUTER_PROMPT_TEMPLATE.format(
            query=query,
            num_docs=num_docs,
            has_history=has_history,
            history_preview=history_preview,
        )
        messages = [
            SystemMessage(content=_ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = self._llm.invoke(messages)
            return self._parse_routing_response(response.content, num_docs)
        except Exception as exc:
            logger.warning(
                "LLM routing failed, using fallback",
                extra={"error": str(exc)},
            )
            return self._fallback_route(query, num_docs, has_history)

    def _parse_routing_response(self, raw: str, num_docs: int) -> AgentType:
        """
        Parse the JSON routing response from Gemini.
        Handles markdown code fences and malformed JSON gracefully.
        """
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("```").strip()

        try:
            obj = json.loads(cleaned)
            agent_str = obj.get("agent", "rag").lower()
            confidence = float(obj.get("confidence", 1.0))

            logger.debug(
                "Router classification",
                extra={
                    "agent": agent_str,
                    "reasoning": obj.get("reasoning", ""),
                    "confidence": confidence,
                },
            )

            # Low confidence + no docs → web
            if confidence < 0.6 and num_docs == 0:
                return AgentType.WEB

            mapping = {"rag": AgentType.RAG, "web": AgentType.WEB, "memory": AgentType.MEMORY}
            return mapping.get(agent_str, AgentType.RAG)

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Could not parse router JSON",
                extra={"raw": raw[:200], "error": str(exc)},
            )
            return AgentType.RAG if num_docs > 0 else AgentType.WEB

    @staticmethod
    def _fallback_route(query: str, num_docs: int, has_history: bool) -> AgentType:
        """
        Rule-based fallback routing when LLM classification fails.
        """
        q_lower = query.lower()

        memory_keywords = {"earlier", "before", "previous", "you said", "last time", "continue"}
        web_keywords = {"latest", "current", "today", "news", "recent", "2024", "2025", "live"}

        if has_history and any(kw in q_lower for kw in memory_keywords):
            return AgentType.MEMORY
        if any(kw in q_lower for kw in web_keywords):
            return AgentType.WEB
        return AgentType.RAG if num_docs > 0 else AgentType.WEB

    @staticmethod
    def _preview_history(state: AgentState) -> str:
        """Return a short preview of the conversation history."""
        if not state.conversation_history:
            return "None"
        last = state.conversation_history[-1]
        return f"{last.role.value}: {last.content[:100]}..."


# ── Module-level singleton ─────────────────────────────────────────────────────

_router: RouterAgent | None = None


def get_router() -> RouterAgent:
    """Return the singleton RouterAgent instance."""
    global _router
    if _router is None:
        _router = RouterAgent()
    return _router
