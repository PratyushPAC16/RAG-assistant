"""
Enterprise Agentic RAG Assistant
LangGraph workflow — assembles the full multi-agent graph with typed state,
conditional edges, a response formatter node, and graph visualisation.

Graph topology:
    START → router_node → (rag_node | web_node | memory_node) → formatter_node → END
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.memory_agent import MemoryAgent, get_memory_agent
from app.agents.rag_agent import RAGAgent, get_rag_agent
from app.agents.router import RouterAgent, get_router
from app.agents.web_agent import WebSearchAgent, get_web_agent
from app.models.schemas import AgentState, AgentType, ChatMessage, MessageRole, RoutingDecision, MemoryRecord
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


# ── State type for LangGraph ───────────────────────────────────────────────────

def merge_latency(left: dict[str, float] | None, right: dict[str, float] | None) -> dict[str, float]:
    res = {}
    if left:
        res.update(left)
    if right:
        res.update(right)
    return res


def merge_memories(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    if not left:
        return right or []
    if not right:
        return left or []
    seen = set()
    res = []
    for m in (left + right):
        mid = getattr(m, "memory_id", None) if not isinstance(m, dict) else m.get("memory_id")
        if mid:
            if mid not in seen:
                seen.add(mid)
                res.append(m)
        else:
            res.append(m)
    return res


def merge_agent_type(left: AgentType | str | None, right: AgentType | str | None) -> AgentType | str | None:
    if left == AgentType.HYBRID or left == "hybrid" or right == AgentType.HYBRID or right == "hybrid":
        return AgentType.HYBRID
    if left and right and left != right:
        return AgentType.HYBRID
    return left or right


def merge_retrieved_chunks(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    if not left:
        return right or []
    if not right:
        return left or []
    seen = set()
    res = []
    for c in (left + right):
        cid = getattr(c, "chunk_id", None) if not isinstance(c, dict) else c.get("chunk_id")
        if cid:
            if cid not in seen:
                seen.add(cid)
                res.append(c)
        else:
            res.append(c)
    return res


def merge_web_results(left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not left:
        return right or []
    if not right:
        return left or []
    seen = set()
    res = []
    for item in (left + right):
        url = item.get("url") if isinstance(item, dict) else getattr(item, "url", None)
        if url:
            if url not in seen:
                seen.add(url)
                res.append(item)
        else:
            res.append(item)
    return res


def merge_error(left: str | None, right: str | None) -> str | None:
    if left and right:
        if left == right:
            return left
        return f"{left}; {right}"
    return left or right


def merge_routing_trace(left: list[str] | None, right: list[str] | None) -> list[str]:
    """Concatenate routing trace entries from parallel branches."""
    return (left or []) + (right or [])


def merge_routing_decision(
    left: Any | None, right: Any | None
) -> Any | None:
    """Keep whichever routing decision is present (router sets it once)."""
    return left if left is not None else right


def merge_add_int(left: int | None, right: int | None) -> int:
    """Sum integers across parallel branches."""
    return (left or 0) + (right or 0)


def merge_add_float(left: float | None, right: float | None) -> float:
    """Sum floats across parallel branches."""
    return (left or 0.0) + (right or 0.0)


def merge_filter_document_ids(left: list[str] | None, right: list[str] | None) -> list[str] | None:
    """Keep document filter IDs (they don't change)."""
    return right if right is not None else left


class GraphState(TypedDict):
    query: str
    session_id: str
    agent_type: Annotated[AgentType | str | None, merge_agent_type]
    retrieved_chunks: Annotated[list[Any], merge_retrieved_chunks]
    reranked_chunks: Annotated[list[Any], merge_retrieved_chunks]
    web_results: Annotated[list[dict[str, Any]], merge_web_results]
    context: str
    answer: str
    sources: list[Any]
    conversation_history: list[Any]
    error: Annotated[str | None, merge_error]
    latency_ms: Annotated[dict[str, float], merge_latency]
    routing_decision: Annotated[Any | None, merge_routing_decision]
    routing_trace: Annotated[list[str], merge_routing_trace]
    prompt_tokens: Annotated[int, merge_add_int]
    completion_tokens: Annotated[int, merge_add_int]
    total_tokens: Annotated[int, merge_add_int]
    cost_usd: Annotated[float, merge_add_float]
    filter_document_ids: Annotated[list[str] | None, merge_filter_document_ids]
    retrieved_memories: Annotated[list[Any], merge_memories]



def _state_to_dict(state: AgentState) -> dict[str, Any]:
    return state.model_dump()


def _dict_to_state(d: dict[str, Any]) -> AgentState:
    return AgentState.model_validate(d)


# ── Node functions ─────────────────────────────────────────────────────────────

def memory_retriever_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: retrieve relevant memories from long-term memory store.
    """
    t0 = time.perf_counter()
    from datetime import datetime
    agent_state = _dict_to_state(state)
    agent_state.routing_trace.append("🧠 Long-Term Memory: searching for relevant user preferences and facts…")
    
    from app.memory.memory_store import get_memory_store
    from app.models.schemas import MemoryRecord
    
    store = get_memory_store()
    results = store.search_memories(agent_state.query, top_k=5, score_threshold=0.45)
    
    retrieved_memories = []
    for r in results:
        ts = r["timestamp"]
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts)
            except ValueError:
                dt = datetime.now(timezone.utc)
        else:
            dt = ts or datetime.now(timezone.utc)
            
        retrieved_memories.append(MemoryRecord(
            memory_id=r["memory_id"],
            content=r["content"],
            memory_type=r["memory_type"],
            session_id=r["session_id"],
            score=r["score"],
            timestamp=dt
        ))
    
    agent_state.retrieved_memories = retrieved_memories
    if retrieved_memories:
        trace_entry = f"🧠 Long-Term Memory: found {len(retrieved_memories)} relevant memory/memories"
    else:
        trace_entry = "🧠 Long-Term Memory: no relevant memories found"
        
    elapsed = (time.perf_counter() - t0) * 1000
    agent_state.latency_ms["memory"] = round(elapsed, 2)
    
    serialized = _state_to_dict(agent_state)
    serialized["routing_trace"] = [trace_entry]
    serialized["retrieved_memories"] = [m.model_dump(mode="json") for m in retrieved_memories]
    return serialized


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
    agent_state.routing_trace.append("📚 RAG Agent: starting hybrid retrieval (ChromaDB + BM25)…")
    rag = get_rag_agent()
    updated = rag.run(agent_state)
    serialized = _state_to_dict(updated)
    num_retrieved = len(serialized.get("retrieved_chunks", []))
    num_reranked = len(serialized.get("reranked_chunks", []))
    trace_entry = (
        f"📚 RAG Agent: retrieved {num_retrieved} chunks, "
        f"reranked to top {num_reranked}"
    )
    return {
        "retrieved_chunks": serialized.get("retrieved_chunks", []),
        "reranked_chunks": serialized.get("reranked_chunks", []),
        "latency_ms": serialized.get("latency_ms", {}),
        "agent_type": serialized.get("agent_type"),
        "error": serialized.get("error"),
        "routing_trace": [trace_entry],
    }


def web_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: run web search pipeline (Tavily → summarise).
    """
    agent_state = _dict_to_state(state)
    agent_state.routing_trace.append("🌐 Web Search Agent: querying Tavily…")
    web = get_web_agent()
    updated = web.run(agent_state)
    serialized = _state_to_dict(updated)
    num_results = len(serialized.get("web_results", []))
    trace_entry = f"🌐 Web Search Agent: found {num_results} web results"
    return {
        "web_results": serialized.get("web_results", []),
        "latency_ms": serialized.get("latency_ms", {}),
        "agent_type": serialized.get("agent_type"),
        "error": serialized.get("error"),
        "routing_trace": [trace_entry],
    }


def memory_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: answer using conversation memory.
    """
    t0 = time.perf_counter()
    agent_state = _dict_to_state(state)
    agent_state.routing_trace.append("🧠 Memory Agent: retrieving conversation history…")
    memory = get_memory_agent()
    updated = memory.run(agent_state)
    elapsed = (time.perf_counter() - t0) * 1000
    updated.latency_ms["memory_agent"] = round(elapsed, 2)
    serialized = _state_to_dict(updated)
    trace_entry = "🧠 Memory Agent: context loaded from session history"
    return {
        "conversation_history": serialized.get("conversation_history", []),
        "latency_ms": serialized.get("latency_ms", {}),
        "agent_type": serialized.get("agent_type"),
        "error": serialized.get("error"),
        "routing_trace": [trace_entry],
    }


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
    total = sum(v for k, v in agent_state.latency_ms.items() if not k.startswith("num_"))
    agent_state.latency_ms["total"] = round(total, 2)

    # Final trace entry
    agent_state.routing_trace.append(
        f"✅ Pipeline complete | Agent: {(agent_state.agent_type or 'unknown')} | "
        f"Sources: {len(agent_state.sources)} | Total: {total:.0f}ms"
    )

    logger.info(
        "Response formatted",
        extra={
            "agent": (agent_state.agent_type or "unknown"),
            "total_latency_ms": total,
            "num_sources": len(agent_state.sources),
            "routing_trace_steps": len(agent_state.routing_trace),
        },
    )

    return _state_to_dict(agent_state)


def synthesizer_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node: synthesize responses from the gathered contexts.
    """
    agent_state = _dict_to_state(state)
    agent_state.routing_trace.append("✨ Response Synthesizer: generating answer from context…")
    from app.agents.synthesizer import get_synthesizer
    synth = get_synthesizer()
    updated = synth.run(agent_state)
    serialized = _state_to_dict(updated)
    num_sources = len(serialized.get("sources", []))
    result = _state_to_dict(updated)
    result["routing_trace"] = [f"✨ Response Synthesizer: answer generated with {num_sources} source(s)"]
    return result


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
    Construct and compile the full LangGraph StateGraph (retrieval + synthesis).

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
    graph = StateGraph(GraphState)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("memory_retriever_node", memory_retriever_node)
    graph.add_node("router_node", router_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("web_node", web_node)
    graph.add_node("memory_node", memory_node)
    graph.add_node("synthesizer_node", synthesizer_node)
    graph.add_node("formatter_node", formatter_node)

    # ── Entry edge ─────────────────────────────────────────────────────────────
    graph.add_edge(START, "memory_retriever_node")
    graph.add_edge("memory_retriever_node", "router_node")

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


def build_retrieval_graph() -> Any:
    """
    Compile a **retrieval-only** subgraph — identical to :func:`build_graph`
    but stopping immediately after the agent nodes (RAG / web / memory).

    Used by the streaming endpoint:  this graph gathers context (chunks,
    web results, memories) and the caller then streams synthesis separately
    so the LLM tokens can be pushed to the client as they arrive.

    Graph topology::

        START
          │
        memory_retriever_node
          │
        router_node
          │
       ┌──┴──────────┬────────────┐
     rag_node    web_node   memory_node
       └──┬──────────┴────────────┘
          │
         END   ← no synthesizer / formatter

    Returns:
        Compiled LangGraph :class:`CompiledGraph`.
    """
    graph = StateGraph(GraphState)

    graph.add_node("memory_retriever_node", memory_retriever_node)
    graph.add_node("router_node", router_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("web_node", web_node)
    graph.add_node("memory_node", memory_node)

    graph.add_edge(START, "memory_retriever_node")
    graph.add_edge("memory_retriever_node", "router_node")

    graph.add_conditional_edges(
        "router_node",
        _routing_decision,
        {
            "rag_node": "rag_node",
            "web_node": "web_node",
            "memory_node": "memory_node",
        },
    )

    # Converge all agent branches directly to END
    graph.add_edge("rag_node", END)
    graph.add_edge("web_node", END)
    graph.add_edge("memory_node", END)

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
        self._retrieval_graph = build_retrieval_graph()
        self._memory_agent = get_memory_agent()
        logger.info("AgentOrchestrator ready — LangGraph compiled (full + retrieval-only)")

    def run(
        self,
        query: str,
        session_id: str | None = None,
        conversation_history: list[ChatMessage] | None = None,
        use_web_search: bool = True,
        filter_document_ids: list[str] | None = None,
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
            filter_document_ids:  Optional list of document IDs to restrict search.

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
            filter_document_ids=filter_document_ids,
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
            metadata = {
                "sources": [s.model_dump() for s in final_state.sources],
                "latency_ms": final_state.latency_ms,
                "routing_decision": final_state.routing_decision.model_dump() if final_state.routing_decision else None,
                "routing_trace": final_state.routing_trace,
                "prompt_tokens": final_state.prompt_tokens,
                "completion_tokens": final_state.completion_tokens,
                "total_tokens": final_state.total_tokens,
                "cost_usd": final_state.cost_usd,
                "retrieved_memories": [m.model_dump(mode="json") for m in final_state.retrieved_memories],
            }
            self._memory_agent.add_to_memory(
                session_id=sid,
                role=MessageRole.ASSISTANT,
                content=final_state.answer,
                agent_type=final_state.agent_type,
                metadata=metadata,
            )

        # ── Trigger Long-Term Memory Extraction ─────────────────────────────────
        if final_state.answer:
            from app.memory.long_term_memory import extract_and_persist_memory

            def _safe_extract_memory(sid: str, q: str, ans: str) -> None:
                try:
                    extract_and_persist_memory(sid, q, ans)
                except Exception as exc:
                    logger.error(
                        "Long-term memory extraction failed",
                        extra={"session_id": sid, "error": str(exc)},
                        exc_info=True,
                    )

            threading.Thread(
                target=_safe_extract_memory,
                args=(sid, query, final_state.answer),
                daemon=True,
            ).start()

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

    def run_retrieval(
        self,
        query: str,
        session_id: str,
        filter_document_ids: list[str] | None = None,
    ) -> AgentState:
        """
        Run only the retrieval phase (memory → router → RAG/web/memory agents),
        stopping **before** synthesis.  The returned :class:`AgentState` contains
        ``retrieved_chunks``, ``reranked_chunks``, ``web_results``,
        ``retrieved_memories``, ``conversation_history``, ``agent_type``,
        and ``routing_trace`` — everything the synthesizer needs.

        Used exclusively by the ``/chat/stream`` endpoint so synthesis can be
        streamed independently after context is gathered.

        Args:
            query:               The user's question.
            session_id:          Session ID for memory continuity.
            filter_document_ids: Optional document ID filter.

        Returns:
            Partially-complete :class:`AgentState` (no ``answer`` yet).
        """
        stored_history = self._memory_agent.get_session_history(session_id)
        initial_state = AgentState(
            query=query,
            session_id=session_id,
            conversation_history=stored_history,
            filter_document_ids=filter_document_ids,
        )
        with log_latency(logger, "retrieval_pipeline", session_id=session_id, query=query):
            raw = self._retrieval_graph.invoke(_state_to_dict(initial_state))
        return _dict_to_state(raw)

    def persist_exchange(
        self,
        session_id: str,
        query: str,
        final_state: AgentState,
    ) -> None:
        """
        Save the user query and assistant answer to session memory, and trigger
        background long-term memory extraction.  Called by the streaming
        endpoint once the full answer has been assembled from stream chunks.
        """
        self._memory_agent.add_to_memory(
            session_id=session_id,
            role=MessageRole.USER,
            content=query,
        )
        if final_state.answer:
            metadata = {
                "sources": [s.model_dump() for s in final_state.sources],
                "latency_ms": final_state.latency_ms,
                "routing_decision": final_state.routing_decision.model_dump() if final_state.routing_decision else None,
                "routing_trace": final_state.routing_trace,
                "prompt_tokens": final_state.prompt_tokens,
                "completion_tokens": final_state.completion_tokens,
                "total_tokens": final_state.total_tokens,
                "cost_usd": final_state.cost_usd,
                "retrieved_memories": [m.model_dump(mode="json") for m in final_state.retrieved_memories],
            }
            self._memory_agent.add_to_memory(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=final_state.answer,
                agent_type=final_state.agent_type,
                metadata=metadata,
            )
            from app.memory.long_term_memory import extract_and_persist_memory

            def _safe_extract(sid: str, q: str, ans: str) -> None:
                try:
                    extract_and_persist_memory(sid, q, ans)
                except Exception as exc:
                    logger.error(
                        "Long-term memory extraction failed",
                        extra={"session_id": sid, "error": str(exc)},
                        exc_info=True,
                    )

            threading.Thread(
                target=_safe_extract,
                args=(session_id, query, final_state.answer),
                daemon=True,
            ).start()

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
_orchestrator_lock = threading.Lock()


def get_orchestrator() -> AgentOrchestrator:
    """Return the singleton AgentOrchestrator instance (thread-safe)."""
    global _orchestrator
    with _orchestrator_lock:
        if _orchestrator is None:
            _orchestrator = AgentOrchestrator()
    return _orchestrator
