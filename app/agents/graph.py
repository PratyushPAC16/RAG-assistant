"""
Enterprise Agentic RAG Assistant
LangGraph workflow — assembles the full multi-agent graph with typed state,
conditional edges, a response formatter node, and graph visualisation.

Graph topology:
    START → router_node → (rag_node | web_node | memory_node) → formatter_node → END
"""

from __future__ import annotations

import json
import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.memory_agent import MemoryAgent, get_memory_agent
from app.agents.rag_agent import RAGAgent, get_rag_agent
from app.agents.router import RouterAgent, get_router
from app.agents.web_agent import WebSearchAgent, get_web_agent
from app.models.schemas import AgentState, AgentType, ChatMessage, MessageRole
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


# ── State type for LangGraph ───────────────────────────────────────────────────
# LangGraph requires a TypedDict or plain dict; we use a wrapper that converts
# our Pydantic AgentState to/from dict transparently.

def _state_to_dict(state: AgentState) -> dict[str, Any]:
    return state.model_dump()


def _dict_to_state(d: dict[str, Any]) -> AgentState:
    return AgentState.model_validate(d)


# ── Node functions ─────────────────────────────────────────────────────────────

def router_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: classify query and set ``agent_type``.
    """
    agent_state = _dict_to_state(state)
    router = get_router()
    updated = router.route(agent_state)
    return _state_to_dict(updated)


def rag_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: run RAG pipeline (retrieve → rerank → generate).
    """
    agent_state = _dict_to_state(state)
    rag = get_rag_agent()
    updated = rag.run(agent_state)
    return _state_to_dict(updated)


def web_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: run web search pipeline (Tavily → summarise).
    """
    agent_state = _dict_to_state(state)
    web = get_web_agent()
    updated = web.run(agent_state)
    return _state_to_dict(updated)


def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: answer using conversation memory.
    """
    agent_state = _dict_to_state(state)
    memory = get_memory_agent()
    updated = memory.run(agent_state)
    return _state_to_dict(updated)


def formatter_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: post-process the answer — clean whitespace, ensure
    citations are deduplicated, add total latency to state.
    """
    agent_state = _dict_to_state(state)

    # Tidy up the answer
    if agent_state.answer:
        agent_state.answer = agent_state.answer.strip()

    # Deduplicate sources
    seen: set[tuple[str, int | None]] = set()
    deduped = []
    for src in agent_state.sources:
        key = (src.document, src.page)
        if key not in seen:
            seen.add(key)
            deduped.append(src)
    agent_state.sources = deduped

    # Total latency
    total = sum(agent_state.latency_ms.values())
    agent_state.latency_ms["total"] = round(total, 2)

    logger.info(
        "Response formatted",
        extra={
            "agent": (agent_state.agent_type or "unknown"),
            "total_latency_ms": total,
            "num_sources": len(agent_state.sources),
        },
    )

    return _state_to_dict(agent_state)


def synthesizer_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: synthesize responses from the gathered contexts.
    """
    agent_state = _dict_to_state(state)
    from app.agents.synthesizer import get_synthesizer
    synth = get_synthesizer()
    updated = synth.run(agent_state)
    return _state_to_dict(updated)


def _routing_decision(state: dict[str, Any]) -> list[str]:
    """
    LangGraph conditional edge: return next node name(s) based on ``agent_type``.
    Supports parallel branching for hybrid queries.
    """
    agent_type_val = state.get("agent_type")

    if agent_type_val == AgentType.HYBRID.value:
        return ["rag_node", "web_node"]

    mapping = {
        AgentType.RAG.value: ["rag_node"],
        AgentType.WEB.value: ["web_node"],
        AgentType.MEMORY.value: ["memory_node"],
    }
    return mapping.get(agent_type_val or "", ["rag_node"])


# ── Graph construction ─────────────────────────────────────────────────────────

def build_graph() -> Any:
    """
    Construct and compile the LangGraph StateGraph.

    Graph topology::

        START
          │
        router_node          (classifies query → sets agent_type)
          │
       ┌──┴──────────┬────────────┐
     rag_node    web_node   memory_node
       └──┬──────────┴────────────┘
          │
     synthesizer_node        (runs LLM response synthesis)
          │
     formatter_node          (cleans up response)
          │
         END

    Returns:
        Compiled LangGraph :class:`CompiledGraph` ready for ``.invoke()``.
    """
    graph = StateGraph(dict)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("router_node", router_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("web_node", web_node)
    graph.add_node("memory_node", memory_node)
    graph.add_node("synthesizer_node", synthesizer_node)
    graph.add_node("formatter_node", formatter_node)

    # ── Entry edge ─────────────────────────────────────────────────────────────
    graph.add_edge(START, "router_node")

    # ── Conditional routing edge ───────────────────────────────────────────────
    graph.add_conditional_edges(
        "router_node",
        _routing_decision,
        {
            "rag_node": "rag_node",
            "web_node": "web_node",
            "memory_node": "memory_node",
        },
    )

    # ── Convergence edges → synthesizer ────────────────────────────────────────
    graph.add_edge("rag_node", "synthesizer_node")
    graph.add_edge("web_node", "synthesizer_node")
    graph.add_edge("memory_node", "synthesizer_node")

    # ── Terminal edges ─────────────────────────────────────────────────────────
    graph.add_edge("synthesizer_node", "formatter_node")
    graph.add_edge("formatter_node", END)

    return graph.compile()


# ── Top-level orchestrator class ───────────────────────────────────────────────

class AgentOrchestrator:
    """
    High-level interface for running the LangGraph workflow.

    Usage::

        orchestrator = AgentOrchestrator()
        result = orchestrator.run(
            query="What is the revenue forecast?",
            session_id="abc123",
            conversation_history=[...],
        )
        print(result.answer)
        print(result.sources)
    """

    def __init__(self) -> None:
        self._graph = build_graph()
        self._memory_agent = get_memory_agent()
        logger.info("AgentOrchestrator ready — LangGraph compiled")

    def run(
        self,
        query: str,
        session_id: str | None = None,
        conversation_history: list[ChatMessage] | None = None,
        use_web_search: bool = True,
    ) -> AgentState:
        """
        Execute the full agentic pipeline for a user query.

        1. Build an :class:`~app.models.schemas.AgentState`.
        2. Invoke the compiled LangGraph.
        3. Persist user + assistant messages to session memory.
        4. Return the final :class:`~app.models.schemas.AgentState`.

        Args:
            query:                The user's question.
            session_id:           Session identifier for memory continuity.
            conversation_history: Previous messages to inject into state.
            use_web_search:       Whether web routing is allowed.

        Returns:
            Final :class:`~app.models.schemas.AgentState` with answer and sources.
        """
        import uuid

        sid = session_id or uuid.uuid4().hex

        # Merge stored memory with any history passed by caller
        stored_history = self._memory_agent.get_session_history(sid)
        merged_history = stored_history + (conversation_history or [])

        initial_state = AgentState(
            query=query,
            session_id=sid,
            conversation_history=merged_history,
        )

        with log_latency(logger, "full_pipeline", session_id=sid, query=query):
            raw_result = self._graph.invoke(_state_to_dict(initial_state))

        final_state = _dict_to_state(raw_result)

        # ── Persist to session memory ──────────────────────────────────────────
        self._memory_agent.add_to_memory(
            session_id=sid,
            role=MessageRole.USER,
            content=query,
        )
        if final_state.answer:
            self._memory_agent.add_to_memory(
                session_id=sid,
                role=MessageRole.ASSISTANT,
                content=final_state.answer,
                agent_type=final_state.agent_type,
            )

        logger.info(
            "Pipeline complete",
            extra={
                "session_id": sid,
                "agent_used": (final_state.agent_type.value if final_state.agent_type else "unknown"),
                "latency_ms": final_state.latency_ms,
                "num_sources": len(final_state.sources),
            },
        )

        return final_state

    def get_graph_mermaid(self) -> str:
        """
        Return a Mermaid diagram string of the compiled graph for documentation.
        """
        try:
            return self._graph.get_graph().draw_mermaid()
        except Exception:
            # Fallback manual diagram
            return """
graph TD
    START([START]) --> router_node[Router Agent]
    router_node -->|RAG| rag_node[RAG Agent]
    router_node -->|Web| web_node[Web Search Agent]
    router_node -->|Memory| memory_node[Memory Agent]
    router_node -->|Hybrid| rag_node
    router_node -->|Hybrid| web_node
    rag_node --> synthesizer_node[Response Synthesizer]
    web_node --> synthesizer_node
    memory_node --> synthesizer_node
    synthesizer_node --> formatter_node[Response Formatter]
    formatter_node --> END([END])
"""


# ── Module-level singleton ─────────────────────────────────────────────────────

_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """Return the singleton AgentOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
