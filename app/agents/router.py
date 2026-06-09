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

from app.models.schemas import AgentState, AgentType, RoutingDecision
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
4. "hybrid" — For complex queries that compare, combine, or contrast facts in the user's uploaded documents with current web trends/information.

Decision rules:
- If the query references "the document", "the report", "the file", "in the data" AND asks about current/trends/external context → "hybrid"
- If the query references "the document", "the report", "the file", "in the data" only → "rag"
- If the query asks about "latest", "current", "today", "news", "recent" → "web"
- If the query uses "you said", "earlier", "before", "the previous answer", "continue" → "memory"
- If the vector store is empty (no documents indexed), prefer "web" over "rag"
- Default to "rag" when uncertain and documents are available

Respond ONLY with a JSON object in this exact format:
{
  "agent": "<rag|web|memory|hybrid>",
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
    1. Query intent (document, web, memory, hybrid).
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

        Also populates ``state.routing_decision`` with the full classification
        result (agent, reasoning, confidence) and appends step-by-step entries
        to ``state.routing_trace`` for display in the UI.

        Args:
            state: Current :class:`~app.models.schemas.AgentState`.

        Returns:
            State with ``agent_type``, ``routing_decision``, and
            ``routing_trace`` populated.
        """
        query = state.query
        logger.info("RouterAgent.route called", extra={"query": query[:80]})

        state.routing_trace.append(f"⏳ Router received query ({len(query)} chars)")

        try:
            num_docs = self._vector_store.count()
            has_history = bool(state.conversation_history)
            history_preview = self._preview_history(state)

            state.routing_trace.append(
                f"📚 Knowledge base: {num_docs} chunks | "
                f"Conversation history: {'yes' if has_history else 'no'}"
            )

            with log_latency(logger, "routing", query=query) as route_ctx:
                agent_type, decision = self._classify_with_decision(
                    query=query,
                    num_docs=num_docs,
                    has_history=has_history,
                    history_preview=history_preview,
                )
            state.latency_ms["routing"] = route_ctx.get("latency_ms", 0.0)

            state.agent_type = agent_type
            state.routing_decision = decision

            # Build a human-readable routing trace entry
            agent_label = {
                "rag": "RAG Agent 📚",
                "web": "Web Search Agent 🌐",
                "memory": "Memory Agent 🧠",
                "hybrid": "Hybrid Workflow 🔀 (RAG + Web)",
            }.get(agent_type.value, agent_type.value)

            conf_pct = int(decision.confidence * 100)
            fallback_note = " [rule-based fallback]" if decision.fallback_used else ""
            state.routing_trace.append(
                f"→ Route: **{agent_label}** | Confidence: {conf_pct}%{fallback_note}"
            )
            if decision.reasoning:
                state.routing_trace.append(f"💬 Reason: {decision.reasoning}")

            logger.info(
                "Query routed",
                extra={
                    "query": query[:80],
                    "agent": agent_type.value,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning[:120] if decision.reasoning else "",
                    "fallback_used": decision.fallback_used,
                    "num_docs": num_docs,
                },
            )

        except Exception as exc:
            logger.error(
                "RouterAgent.route failed — defaulting to RAG",
                extra={"error": str(exc)},
                exc_info=True,
            )
            state.agent_type = AgentType.RAG
            state.routing_decision = RoutingDecision(
                agent="rag",
                reasoning="Routing failed — defaulting to RAG.",
                confidence=0.5,
                fallback_used=True,
                num_docs_available=0,
            )
            state.routing_trace.append(
                f"⚠️ Routing error: {str(exc)[:80]}. Defaulted to RAG Agent."
            )

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
            AgentType.HYBRID: "hybrid_route",  # Handled in conditional routing
        }
        agent = state.agent_type or AgentType.RAG
        return mapping.get(agent, "rag_node")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _classify_with_decision(
        self,
        query: str,
        num_docs: int,
        has_history: bool,
        history_preview: str,
    ) -> tuple[AgentType, RoutingDecision]:
        """
        Use the LLM to classify the query and return both the AgentType
        and a populated :class:`RoutingDecision`.

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
            return self._parse_routing_response_with_decision(
                response.content, num_docs, query, has_history
            )
        except Exception as exc:
            logger.warning(
                "LLM routing failed, using fallback",
                extra={"error": str(exc)},
            )
            agent_type = self._fallback_route(query, num_docs, has_history)
            decision = RoutingDecision(
                agent=agent_type.value,
                reasoning=f"Rule-based fallback: LLM routing unavailable ({type(exc).__name__})",
                confidence=0.7,
                fallback_used=True,
                num_docs_available=num_docs,
            )
            return agent_type, decision

    def _classify(
        self,
        query: str,
        num_docs: int,
        has_history: bool,
        history_preview: str,
    ) -> AgentType:
        """Convenience wrapper — returns only AgentType (backwards compat)."""
        agent_type, _ = self._classify_with_decision(
            query, num_docs, has_history, history_preview
        )
        return agent_type

    def _parse_routing_response_with_decision(
        self, raw: str, num_docs: int, query: str = "", has_history: bool = False
    ) -> tuple[AgentType, RoutingDecision]:
        """
        Parse the JSON routing response from the LLM.
        Returns both the AgentType and a fully populated RoutingDecision.
        Handles markdown code fences and malformed JSON gracefully.
        """
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("```").strip()

        try:
            obj = json.loads(cleaned)
            agent_str = obj.get("agent", "rag").lower()
            confidence = float(obj.get("confidence", 1.0))
            reasoning = obj.get("reasoning", "")

            logger.debug(
                "Router classification",
                extra={"agent": agent_str, "reasoning": reasoning, "confidence": confidence},
            )

            # Low confidence + no docs → web
            if confidence < 0.6 and num_docs == 0:
                agent_str = "web"

            mapping = {
                "rag": AgentType.RAG,
                "web": AgentType.WEB,
                "memory": AgentType.MEMORY,
                "hybrid": AgentType.HYBRID,
            }
            agent_type = mapping.get(agent_str, AgentType.RAG)

            decision = RoutingDecision(
                agent=agent_type.value,
                reasoning=reasoning,
                confidence=confidence,
                fallback_used=False,
                num_docs_available=num_docs,
            )
            return agent_type, decision

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Could not parse router JSON",
                extra={"raw": raw[:200], "error": str(exc)},
            )
            agent_type = AgentType.RAG if num_docs > 0 else AgentType.WEB
            decision = RoutingDecision(
                agent=agent_type.value,
                reasoning="JSON parse error — using heuristic default.",
                confidence=0.5,
                fallback_used=True,
                num_docs_available=num_docs,
            )
            return agent_type, decision

    def _parse_routing_response(self, raw: str, num_docs: int) -> AgentType:
        """Backwards-compatible wrapper — returns only AgentType."""
        agent_type, _ = self._parse_routing_response_with_decision(raw, num_docs)
        return agent_type

    @staticmethod
    def _fallback_route(query: str, num_docs: int, has_history: bool) -> AgentType:
        """
        Rule-based fallback routing when LLM classification fails.
        """
        q_lower = query.lower()

        memory_keywords = {"earlier", "before", "previous", "you said", "last time", "continue"}
        web_keywords = {"latest", "current", "today", "news", "recent", "2024", "2025", "live", "trends", "trend", "hiring"}
        doc_keywords = {"document", "report", "file", "data", "resume", "pdf", "cv"}

        has_doc_kw = any(kw in q_lower for kw in doc_keywords)
        has_web_kw = any(kw in q_lower for kw in web_keywords)

        if has_history and any(kw in q_lower for kw in memory_keywords):
            return AgentType.MEMORY
        if has_doc_kw and has_web_kw and num_docs > 0:
            return AgentType.HYBRID
        if has_web_kw:
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
