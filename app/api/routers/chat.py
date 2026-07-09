from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.graph import get_orchestrator
from app.models.schemas import (
    AgentType,
    ChatRequest,
    ChatResponse,
    RetrievalMetric,
)
from app.rag.retriever import _compute_score_distribution, get_retriever
from app.api.dependencies import _require_api_key
from app.api.state import _persist_metric, _retrieval_metrics

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Submit a query and receive an AI-generated answer with source citations.

    The system automatically routes the query to the most appropriate agent:
    - **RAG Agent**: Answers from indexed documents.
    - **Web Agent**: Searches the internet for current information.
    - **Memory Agent**: Handles follow-up questions using conversation history.

    Pass the same ``session_id`` across requests to maintain conversation continuity.
    """
    start_time = time.perf_counter()
    session_id = request.session_id or uuid.uuid4().hex

    logger.info(
        "Chat request received",
        extra={"query": request.query[:80], "session_id": session_id},
    )

    try:
        orchestrator = get_orchestrator()
        import asyncio
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: orchestrator.run(
                query=request.query,
                session_id=session_id,
                use_web_search=request.use_web_search,
                filter_document_ids=request.filter_document_ids,
            ),
        )

        # ── Log detailed retrieval analytics metric ────────────────────────────
        total_ms = (time.perf_counter() - start_time) * 1_000
        lms = result.latency_ms

        # Build score distributions from the top reranked chunks
        rerank_scores = [
            c.rerank_score for c in result.reranked_chunks if c.rerank_score is not None
        ]
        rrf_scores = [
            c.semantic_score for c in result.retrieved_chunks if c.semantic_score is not None
        ]

        metric = RetrievalMetric(
            query=request.query,
            query_length=len(request.query),
            agent_type=result.agent_type or AgentType.RAG,
            session_id=session_id,
            # counts
            num_vector_results=int(lms.get("num_vector_results", 0)),
            num_bm25_results=int(lms.get("num_bm25_results", 0)),
            num_retrieved=len(result.retrieved_chunks),
            num_reranked=len(result.reranked_chunks),
            # latencies
            vector_search_latency_ms=lms.get("vector_search", 0.0),
            bm25_search_latency_ms=lms.get("bm25_search", 0.0),
            rrf_fusion_latency_ms=lms.get("rrf_fusion", 0.0),
            retrieval_latency_ms=lms.get("retrieval", 0.0),
            reranking_latency_ms=lms.get("reranking"),
            llm_latency_ms=lms.get("synthesis_llm") or lms.get("llm"),
            total_latency_ms=total_ms,
            # score distributions
            rerank_score_distribution=_compute_score_distribution(rerank_scores),
            rrf_score_distribution=_compute_score_distribution(rrf_scores),
            # sources
            sources_used=[s.document for s in result.sources],
            top_reranked_sources=[
                c.metadata.source for c in result.reranked_chunks[:5]
            ],
            # Token & Cost observability
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost_usd=result.cost_usd,
        )
        _retrieval_metrics.append(metric)
        _persist_metric(metric)

        return ChatResponse(
            answer=result.answer,
            sources=result.sources,
            agent_used=result.agent_type or AgentType.RAG,
            session_id=session_id,
            latency_ms=result.latency_ms,
            routing_decision=result.routing_decision,
            routing_trace=result.routing_trace,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost_usd=result.cost_usd,
            retrieved_memories=result.retrieved_memories,
        )

    except Exception as exc:
        logger.error(
            "Chat request failed",
            extra={"query": request.query[:80], "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query. Check server logs for details.",
        )


@router.get(
    "/chat/sessions",
    summary="List all persistent conversation sessions",
)
async def list_chat_sessions() -> list[dict]:
    """
    Retrieve metadata (session ID, title, last updated timestamp, message count)
    for all conversation histories saved on disk.
    """
    from app.memory.memory_manager import get_memory_manager
    return get_memory_manager().list_sessions()


@router.delete(
    "/chat/session/{session_id}",
    summary="Delete a conversation session",
    dependencies=[Depends(_require_api_key)],
)
async def delete_chat_session(session_id: str) -> dict:
    """
    Clear conversation memory for a session ID and delete its persistent JSON file.
    """
    from app.agents.memory_agent import get_memory_agent
    get_memory_agent().clear_session(session_id)
    return {"session_id": session_id, "message": "Conversation memory cleared."}


@router.get(
    "/chat/session/{session_id}/export",
    summary="Export conversation history",
)
async def export_chat_session(session_id: str, format: str = "json") -> dict:
    """
    Export the conversation history for a session ID.
    Supports format: json (default) or markdown.
    """
    from app.memory.memory_manager import get_memory_manager
    memory = get_memory_manager().load_session(session_id)
    if not memory:
        from app.agents.memory_agent import get_memory_agent
        messages = get_memory_agent().get_session_history(session_id)
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation session '{session_id}' not found.",
            )
        from app.models.schemas import ConversationMemory
        memory = ConversationMemory(session_id=session_id, messages=messages)

    if format.lower() == "markdown":
        lines = [f"# Chat Conversation: {session_id}", ""]
        for i, msg in enumerate(memory.messages, start=1):
            role_label = "**User**" if msg.role.value == "user" else f"**Assistant ({msg.agent_type.value if msg.agent_type else 'RAG'})**"
            ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S") if msg.timestamp else ""
            lines.append(f"### Turn {i} - {role_label} - *{ts_str}*")
            lines.append(msg.content)
            lines.append("")
        md_text = "\n".join(lines)
        return {"session_id": session_id, "format": "markdown", "content": md_text}

    serialized_msgs = [msg.model_dump(mode="json") for msg in memory.messages]
    return {
        "session_id": session_id,
        "format": "json",
        "messages": serialized_msgs
    }
