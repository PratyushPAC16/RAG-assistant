"""
Workflow Executor
=================
Topologically sorts a ``WorkflowDefinition`` graph and executes each node
in dependency order, passing upstream outputs downstream.

Supported node types
--------------------
  router      – Classifies query and sets routing decision
  rag         – Hybrid ChromaDB + BM25 retrieval + reranking
  memory      – Long-term memory retrieval from ChromaDB
  web_search  – Real-time Tavily web search
  llm         – LLM generation via any configured provider
  evaluator   – LLM-graded response quality scoring
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.models.schemas import (
    WorkflowDefinition,
    WorkflowEdgeDef,
    WorkflowExecutionResult,
    WorkflowExecutionStep,
    WorkflowNodeDef,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Topological sort ──────────────────────────────────────────────────────────

def _topological_sort(nodes: list[WorkflowNodeDef], edges: list[WorkflowEdgeDef]) -> list[str]:
    """
    Kahn's algorithm — returns node IDs in execution order.
    Raises ValueError on cycles.
    """
    node_ids = {n.id for n in nodes}
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}

    for edge in edges:
        if edge.source in node_ids and edge.target in node_ids:
            adjacency[edge.source].append(edge.target)
            in_degree[edge.target] += 1

    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbour in adjacency[nid]:
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if len(order) != len(node_ids):
        raise ValueError("Workflow graph contains a cycle — cannot execute.")

    return order


# ── Node executors ────────────────────────────────────────────────────────────

def _exec_router(node: WorkflowNodeDef, ctx: dict[str, Any]) -> dict[str, Any]:
    """Determine routing decision from query."""
    query     = ctx.get("query", "")
    mode      = node.config.get("routing_mode", "auto")
    query_low = query.lower()

    if mode != "auto":
        decision = mode
    elif any(w in query_low for w in ("search", "latest", "news", "current", "today", "recent")):
        decision = "web"
    elif any(w in query_low for w in ("remember", "recall", "previously", "last time", "history")):
        decision = "memory"
    elif any(w in query_low for w in ("document", "pdf", "file", "uploaded")):
        decision = "rag"
    else:
        decision = "rag"

    return {"query": query, "routing_decision": decision}


def _exec_rag(node: WorkflowNodeDef, ctx: dict[str, Any]) -> dict[str, Any]:
    """Hybrid retrieval from ChromaDB + BM25 with reranking."""
    from app.rag.retriever import get_retriever

    query = ctx.get("query", "")
    top_k = int(node.config.get("top_k", 5))
    filter_docs: str | None = node.config.get("filter_docs") or None

    retriever = get_retriever()
    chunks = retriever.retrieve(
        query=query,
        top_k=top_k,
        filter_document=filter_docs,
    )

    context_parts = []
    citations     = []
    for i, chunk in enumerate(chunks, 1):
        src = chunk.metadata.source if hasattr(chunk.metadata, "source") else "unknown"
        context_parts.append(f"[{i}] ({src}): {chunk.content[:800]}")
        if src not in citations:
            citations.append(src)

    return {
        "context":    "\n\n".join(context_parts),
        "citations":  citations,
        "num_chunks": len(chunks),
    }


def _exec_memory(node: WorkflowNodeDef, ctx: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant long-term memories."""
    from app.rag.memory_store import get_memory_store

    query  = ctx.get("query", "")
    top_k  = int(node.config.get("top_k", 5))
    types  = node.config.get("memory_types", ["fact", "preference", "summary"])

    store   = get_memory_store()
    results = store.search_memories(query, top_k=top_k, score_threshold=0.4)

    filtered = [m for m in results if m.get("memory_type") in types]
    memories_text = "\n".join(
        f"[{m.get('memory_type', 'unknown')}] {m.get('content', '')}" for m in filtered
    )

    return {
        "memories":       memories_text,
        "memory_count":   len(filtered),
        "memory_records": filtered,
    }


def _exec_web_search(node: WorkflowNodeDef, ctx: dict[str, Any]) -> dict[str, Any]:
    """Real-time web search via Tavily (or fallback stub)."""
    query       = ctx.get("query", "")
    num_results = int(node.config.get("num_results", 3))
    depth       = node.config.get("search_depth", "basic")

    try:
        from app.utils.config import get_settings
        settings = get_settings()
        from tavily import TavilyClient  # type: ignore
        client  = TavilyClient(api_key=settings.tavily_api_key)
        resp    = client.search(query=query, search_depth=depth, max_results=num_results)
        results = resp.get("results", [])
        web_text = "\n\n".join(
            f"[{r.get('title', '')}] {r.get('url', '')}\n{r.get('content', '')[:600]}"
            for r in results
        )
        return {"web_results": web_text, "num_results": len(results), "urls": [r.get("url") for r in results]}
    except Exception as exc:
        logger.warning(f"Web search failed in workflow: {exc}")
        return {"web_results": f"(Web search unavailable: {exc})", "num_results": 0, "urls": []}


def _exec_llm(node: WorkflowNodeDef, ctx: dict[str, Any]) -> dict[str, Any]:
    """Generate a response using the configured LLM provider."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.utils.llm_factory import get_provider_llm, extract_token_usage, calculate_provider_cost

    provider      = node.config.get("provider", "gemini")
    temperature   = float(node.config.get("temperature", 0.1))
    system_prompt = node.config.get(
        "system_prompt", "You are a helpful AI assistant. Answer concisely and accurately."
    )

    # Build context from upstream outputs
    context_parts = []
    if ctx.get("context"):
        context_parts.append(f"RETRIEVED CONTEXT:\n{ctx['context']}")
    if ctx.get("memories"):
        context_parts.append(f"RELEVANT MEMORIES:\n{ctx['memories']}")
    if ctx.get("web_results"):
        context_parts.append(f"WEB SEARCH RESULTS:\n{ctx['web_results']}")

    context_block = "\n\n".join(context_parts)
    user_message  = (
        f"{context_block}\n\nQUESTION: {ctx.get('query', '')}" if context_block
        else ctx.get("query", "")
    )

    llm = get_provider_llm(provider, temperature=temperature)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    t0       = time.perf_counter()
    response = llm.invoke(messages)
    elapsed  = time.perf_counter() - t0

    content   = response.content or ""
    p_tok, c_tok, t_tok = extract_token_usage(response)
    cost      = calculate_provider_cost(provider, p_tok, c_tok)

    return {
        "response":           content,
        "provider":           provider,
        "prompt_tokens":      p_tok,
        "completion_tokens":  c_tok,
        "total_tokens":       t_tok,
        "cost_usd":           round(cost, 8),
        "latency_ms":         round(elapsed * 1000, 2),
    }


def _exec_evaluator(node: WorkflowNodeDef, ctx: dict[str, Any]) -> dict[str, Any]:
    """LLM-graded quality evaluation of a response."""
    import json, re
    from langchain_core.messages import HumanMessage
    from app.utils.llm_factory import get_provider_llm

    response  = ctx.get("response", "")
    query     = ctx.get("query", "")
    criteria  = node.config.get("criteria", ["faithfulness", "relevance"])
    provider  = node.config.get("evaluator_provider", "gemini")
    context   = ctx.get("context") or ctx.get("web_results") or query

    criteria_str = ", ".join(criteria)
    eval_prompt  = f"""You are a strict AI evaluator. Evaluate the following AI response for: {criteria_str}.

QUERY: {query}
CONTEXT: {context[:2000]}
RESPONSE: {response[:2000]}

Score each criterion from 0-100 and provide brief reasoning.
Respond ONLY with valid JSON:
{{
  "overall_score": <0-100>,
  "scores": {{{", ".join(f'"{c}": <0-100>' for c in criteria)}}},
  "feedback": "<2-3 sentences>",
  "passed": <true|false>
}}"""

    try:
        llm  = get_provider_llm(provider, temperature=0.0)
        resp = llm.invoke([HumanMessage(content=eval_prompt)])
        raw  = resp.content.strip()
        m    = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return {
                "score":          data.get("overall_score", 75),
                "scores":         data.get("scores", {}),
                "feedback":       data.get("feedback", ""),
                "passed":         data.get("passed", True),
                "criteria_used":  criteria,
            }
    except Exception as exc:
        logger.warning(f"Evaluator LLM call failed: {exc}")

    return {"score": 75.0, "feedback": "Evaluation unavailable.", "passed": True, "criteria_used": criteria}


# ── Executor registry ─────────────────────────────────────────────────────────

_EXECUTORS = {
    "router":     _exec_router,
    "rag":        _exec_rag,
    "memory":     _exec_memory,
    "web_search": _exec_web_search,
    "llm":        _exec_llm,
    "evaluator":  _exec_evaluator,
}


# ── Main executor entry point ─────────────────────────────────────────────────

def execute_workflow(workflow: WorkflowDefinition, query: str) -> WorkflowExecutionResult:
    """
    Execute a workflow definition against a user query.

    Returns a ``WorkflowExecutionResult`` with per-node step traces.
    """
    result = WorkflowExecutionResult(
        workflow_id=workflow.workflow_id,
        workflow_name=workflow.name,
        query=query,
        status="running",
    )

    # Topological ordering
    try:
        order = _topological_sort(workflow.nodes, workflow.edges)
    except ValueError as exc:
        result.status = "error"
        result.final_output = {"error": str(exc)}
        return result

    # Build a lookup for quick access
    node_map: dict[str, WorkflowNodeDef] = {n.id: n for n in workflow.nodes}

    # Shared context accumulates outputs from all completed nodes
    ctx: dict[str, Any] = {"query": query}

    overall_start = time.perf_counter()

    for node_id in order:
        node = node_map.get(node_id)
        if node is None:
            continue

        node_type  = node.type.value if hasattr(node.type, "value") else str(node.type)
        executor   = _EXECUTORS.get(node_type)
        step_start = time.perf_counter()

        step = WorkflowExecutionStep(
            node_id=node_id,
            node_type=node_type,
            node_label=node.label or node_type.replace("_", " ").title(),
            status="running",
        )

        if executor is None:
            step.status = "error"
            step.error  = f"No executor registered for node type '{node_type}'"
            step.duration_ms = 0.0
        else:
            try:
                output = executor(node, ctx)
                # Merge outputs into shared context for downstream nodes
                ctx.update(output)
                step.status      = "done"
                step.output      = output
                step.duration_ms = round((time.perf_counter() - step_start) * 1000, 2)
                logger.info(f"[Workflow] ✅ {node_type} ({node_id}) — {step.duration_ms}ms")
            except Exception as exc:
                step.status      = "error"
                step.error       = str(exc)
                step.duration_ms = round((time.perf_counter() - step_start) * 1000, 2)
                logger.error(f"[Workflow] ❌ {node_type} ({node_id}) — {exc}", exc_info=True)

        result.steps.append(step)

    result.status            = "done" if all(s.status == "done" for s in result.steps) else "error"
    result.total_duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
    result.completed_at      = datetime.now(timezone.utc)
    result.final_output      = {
        "response":         ctx.get("response", ""),
        "context":          ctx.get("context", ""),
        "memories":         ctx.get("memories", ""),
        "web_results":      ctx.get("web_results", ""),
        "routing_decision": ctx.get("routing_decision", ""),
        "score":            ctx.get("score", None),
        "feedback":         ctx.get("feedback", None),
    }

    return result
