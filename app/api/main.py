"""
Enterprise Agentic RAG Assistant
FastAPI backend — document management and chat endpoints.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.graph import AgentOrchestrator, get_orchestrator
from app.models.schemas import (
    AgentType,
    ChatRequest,
    ChatResponse,
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentStatus,
    FileType,
    HealthResponse,
    MessageRole,
    RetrievalMetric,
    RoutingDecision,
    ScoreDistribution,
    SourceCitation,
    UploadResponse,
    MemoryRecord,
)
from app.rag.document_processor import DocumentProcessor
from app.rag.retriever import get_retriever
from app.rag.vector_store import VectorStore, get_vector_store
from app.utils.config import get_settings
from app.utils.logger import configure_logging, get_logger, set_request_id

settings = get_settings()
configure_logging(level=settings.log_level, fmt=settings.log_format)
logger = get_logger(__name__)

# ── In-memory document registry ───────────────────────────────────────────────
# In production this would be a database; for this project it's an in-process dict.
_document_registry: dict[str, DocumentRecord] = {}

# ── Analytics store ────────────────────────────────────────────────────────────
# ── Analytics store ────────────────────────────────────────────────────────────
_retrieval_metrics: list[RetrievalMetric] = []

# ── Local persistence helper functions ──────────────────────────────────────────

METRICS_FILE = settings.data_path / "retrieval_metrics.jsonl"

def _load_persisted_metrics() -> list[RetrievalMetric]:
    metrics = []
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        metrics.append(RetrievalMetric.model_validate_json(stripped))
            logger.info(f"Loaded {len(metrics)} persisted metrics from {METRICS_FILE}")
        except Exception as exc:
            logger.error(f"Failed to load persisted metrics: {exc}", exc_info=True)
    return metrics

def _persist_metric(metric: RetrievalMetric) -> None:
    try:
        # Ensure parent directory exists
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(metric.model_dump_json() + "\n")
    except Exception as exc:
        logger.error(f"Failed to persist metric: {exc}", exc_info=True)


def _rebuild_document_registry() -> None:
    """Rebuild in-memory registry of documents from ChromaDB collections."""
    global _document_registry
    try:
        vector_store = get_vector_store()
        metadatas = vector_store.get_all_documents_metadata()
        
        # Group chunks by document_id
        doc_chunks = {}
        for meta in metadatas:
            doc_id = meta.get("document_id")
            if doc_id:
                if doc_id not in doc_chunks:
                    doc_chunks[doc_id] = []
                doc_chunks[doc_id].append(meta)
                
        # Rebuild records
        from datetime import datetime
        for doc_id, chunks in doc_chunks.items():
            rep = chunks[0]
            filename = rep.get("document_name") or rep.get("source") or "unknown"
            
            pages = set()
            for c in chunks:
                p = c.get("page")
                if p:
                    pages.add(p)
            num_pages = len(pages) if pages else None
            
            # Infer file type from extension
            ext = Path(filename).suffix.lower().lstrip(".")
            file_type = FileType.TXT
            if ext == "pdf":
                file_type = FileType.PDF
            elif ext == "docx":
                file_type = FileType.DOCX
                
            # Get file size if file exists on disk
            file_size = 0
            save_path = settings.data_path / f"{doc_id}_{filename}"
            if save_path.exists():
                file_size = save_path.stat().st_size
                
            _document_registry[doc_id] = DocumentRecord(
                document_id=doc_id,
                filename=filename,
                file_type=file_type,
                status=DocumentStatus.INDEXED,
                num_chunks=len(chunks),
                num_pages=num_pages,
                file_size_bytes=file_size,
                created_at=datetime.utcnow(),
            )
        logger.info(f"Rebuilt document registry with {len(_document_registry)} documents from ChromaDB")
    except Exception as exc:
        logger.error(f"Failed to rebuild document registry from ChromaDB: {exc}", exc_info=True)


# ── Application lifespan ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup: initialise singletons.
    Shutdown: flush any pending state (placeholder).
    """
    logger.info("Starting Enterprise Agentic RAG Assistant API")

    global _retrieval_metrics
    _retrieval_metrics = _load_persisted_metrics()

    # Warm up singletons on startup to avoid first-request latency
    _ = get_vector_store()
    _rebuild_document_registry()
    _ = get_retriever()
    _ = get_orchestrator()

    logger.info("All services initialised — API ready")
    yield
    logger.info("Shutting down API")


# ── FastAPI application ────────────────────────────────────────────────────────

app = FastAPI(
    title="Enterprise Agentic RAG Assistant",
    description=(
        "Multi-agent Retrieval-Augmented Generation platform. "
        "Upload documents, chat with your knowledge base, and get cited answers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: request-ID injection ───────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request, call_next):
    """Attach a unique request-id to each request for log correlation."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ── Health endpoint ────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
)
async def health_check() -> HealthResponse:
    """
    Return the health status of the API and its dependencies.
    Use this endpoint for readiness/liveness probes.
    """
    vector_store = get_vector_store()
    doc_count = vector_store.count()

    # Determine active models based on provider selection
    if settings.llm_provider.lower() == "gemini":
        active_llm = settings.gemini_model
    elif settings.llm_provider.lower() == "groq":
        active_llm = settings.groq_model
    else:
        active_llm = settings.ollama_model

    if settings.embedding_provider.lower() == "gemini":
        active_emb = settings.embedding_model
    elif settings.embedding_provider.lower() == "local":
        active_emb = settings.local_embedding_model
    else:
        active_emb = settings.ollama_embedding_model

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        vector_store="chromadb",
        embedding_model=active_emb,
        llm_model=active_llm,
        documents_indexed=doc_count,
    )


# ── Document upload ────────────────────────────────────────────────────────────

@app.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
    summary="Upload and index a document",
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a PDF, DOCX, or TXT document.

    The document is saved to disk, processed into chunks, embedded using
    Google Gemini, and stored in ChromaDB for retrieval.

    **Supported formats**: `.pdf`, `.docx`, `.txt`
    """
    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower().lstrip(".")

    if extension not in ("pdf", "docx", "txt"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '.{extension}'. Allowed: pdf, docx, txt",
        )

    document_id = uuid.uuid4().hex
    save_path = settings.data_path / f"{document_id}_{filename}"

    # Register document as pending
    record = DocumentRecord(
        document_id=document_id,
        filename=filename,
        file_type=FileType(extension),
        status=DocumentStatus.PROCESSING,
        file_size_bytes=0,
    )
    _document_registry[document_id] = record

    try:
        # ── Save uploaded file ─────────────────────────────────────────────────
        content = await file.read()
        async with aiofiles.open(save_path, "wb") as f:
            await f.write(content)
        record.file_size_bytes = len(content)

        logger.info(
            "Document uploaded",
            extra={"file_name": filename, "document_id": document_id, "size": len(content)},
        )

        # ── Process and index ──────────────────────────────────────────────────
        processor = DocumentProcessor()
        documents, chunk_metas = processor.process(
            path=save_path, document_id=document_id
        )

        vector_store = get_vector_store()
        vector_store.add_documents(documents, chunk_metas)

        # Refresh BM25 index after adding new documents
        retriever = get_retriever()
        retriever.refresh_bm25_index()

        # ── Update registry ────────────────────────────────────────────────────
        from datetime import datetime

        num_pages = max((m.page or 1) for m in chunk_metas) if chunk_metas else None
        record.status = DocumentStatus.INDEXED
        record.num_chunks = len(documents)
        record.num_pages = num_pages
        record.indexed_at = datetime.utcnow()

        logger.info(
            "Document indexed",
            extra={
                "file_name": filename,
                "document_id": document_id,
                "num_chunks": len(documents),
            },
        )

        return UploadResponse(
            document_id=document_id,
            filename=filename,
            num_chunks=len(documents),
            num_pages=num_pages,
            status=DocumentStatus.INDEXED,
            message=f"Successfully indexed {len(documents)} chunks from '{filename}'.",
        )

    except Exception as exc:
        record.status = DocumentStatus.FAILED
        record.error_message = str(exc)
        logger.error(
            "Document indexing failed",
            extra={"file_name": filename, "error": str(exc)},
            exc_info=True,
        )
        # Clean up saved file on failure
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {exc}",
        )


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
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
        result = orchestrator.run(
            query=request.query,
            session_id=session_id,
            use_web_search=request.use_web_search,
            filter_document_ids=request.filter_document_ids,
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

        def _score_dist(scores: list[float]) -> ScoreDistribution:
            if not scores:
                return ScoreDistribution()
            import math, statistics as _st
            s = sorted(scores)
            n = len(s)
            p90_idx = max(0, int(math.ceil(0.9 * n)) - 1)
            return ScoreDistribution(
                min_score=round(s[0], 6),
                max_score=round(s[-1], 6),
                mean_score=round(_st.mean(s), 6),
                p50_score=round(_st.median(s), 6),
                p90_score=round(s[p90_idx], 6),
            )

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
            rerank_score_distribution=_score_dist(rerank_scores),
            rrf_score_distribution=_score_dist(rrf_scores),
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
            detail=f"Failed to process query: {exc}",
        )


# ── Chat Memory Sessions ───────────────────────────────────────────────────────

@app.get(
    "/chat/sessions",
    tags=["Chat"],
    summary="List all persistent conversation sessions",
)
async def list_chat_sessions() -> list[dict]:
    """
    Retrieve metadata (session ID, title, last updated timestamp, message count)
    for all conversation histories saved on disk.
    """
    from app.utils.memory_manager import get_memory_manager
    return get_memory_manager().list_sessions()


@app.delete(
    "/chat/session/{session_id}",
    tags=["Chat"],
    summary="Delete a conversation session",
)
async def delete_chat_session(session_id: str) -> dict:
    """
    Clear conversation memory for a session ID and delete its persistent JSON file.
    """
    from app.agents.memory_agent import get_memory_agent
    get_memory_agent().clear_session(session_id)
    return {"session_id": session_id, "message": "Conversation memory cleared."}


@app.get(
    "/chat/session/{session_id}/export",
    tags=["Chat"],
    summary="Export conversation history",
)
async def export_chat_session(session_id: str, format: str = "json") -> dict:
    """
    Export the conversation history for a session ID.
    Supports format: json (default) or markdown.
    """
    from app.utils.memory_manager import get_memory_manager
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


# ── Long-Term Memory endpoints ──────────────────────────────────────────────────

@app.get(
    "/memories",
    tags=["Long-Term Memory"],
    summary="List all long-term memories",
)
async def list_all_memories() -> list[dict]:
    """
    Retrieve all stored facts, preferences, and summaries from the ChromaDB long-term memory store.
    """
    from app.rag.memory_store import get_memory_store
    return get_memory_store().list_all_memories()


@app.get(
    "/memories/search",
    tags=["Long-Term Memory"],
    summary="Search matching memories",
)
async def search_memories(query: str, top_k: int = 5) -> list[dict]:
    """
    Query memories matching the user query with similarity scores.
    """
    from app.rag.memory_store import get_memory_store
    return get_memory_store().search_memories(query, top_k=top_k, score_threshold=0.45)


@app.delete(
    "/memories/{memory_id}",
    tags=["Long-Term Memory"],
    summary="Delete a specific long-term memory",
)
async def delete_memory(memory_id: str) -> dict:
    """
    Delete a specific fact/preference/summary from ChromaDB.
    """
    from app.rag.memory_store import get_memory_store
    get_memory_store().delete_memory(memory_id)
    return {"status": "success", "message": f"Memory {memory_id} deleted."}


@app.delete(
    "/memories",
    tags=["Long-Term Memory"],
    summary="Clear all long-term memories",
)
async def clear_all_memories() -> dict:
    """
    Wipe out the entire long-term memories database.
    """
    from app.rag.memory_store import get_memory_store
    get_memory_store().clear_all()
    return {"status": "success", "message": "All long-term memories cleared."}


# ── Document list ──────────────────────────────────────────────────────────────

@app.get(
    "/documents",
    response_model=DocumentListResponse,
    tags=["Documents"],
    summary="List all indexed documents",
)
async def list_documents() -> DocumentListResponse:
    """
    Return a list of all documents that have been uploaded and indexed.
    """
    docs = list(_document_registry.values())
    return DocumentListResponse(documents=docs, total=len(docs))


# ── Document delete ────────────────────────────────────────────────────────────

@app.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentResponse,
    tags=["Documents"],
    summary="Delete a document and its chunks",
)
async def delete_document(document_id: str) -> DeleteDocumentResponse:
    """
    Remove a document and all its associated vector embeddings from the system.

    Args:
        document_id: The UUID of the document to delete.
    """
    if document_id not in _document_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    record = _document_registry[document_id]

    try:
        # Delete from vector store
        vector_store = get_vector_store()
        chunks_deleted = vector_store.delete_by_document_id(document_id)

        # Delete file from disk
        for save_path in settings.data_path.glob(f"{document_id}_*"):
            save_path.unlink()

        # Rebuild BM25 index after deletion
        retriever = get_retriever()
        retriever.refresh_bm25_index()

        # Remove from registry
        del _document_registry[document_id]

        logger.info(
            "Document deleted",
            extra={"document_id": document_id, "chunks_deleted": chunks_deleted},
        )

        return DeleteDocumentResponse(
            document_id=document_id,
            message=f"Document '{record.filename}' deleted successfully.",
            chunks_deleted=chunks_deleted,
        )

    except Exception as exc:
        logger.error(
            "Document deletion failed",
            extra={"document_id": document_id, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {exc}",
        )


@app.post(
    "/documents/{document_id}/reindex",
    response_model=UploadResponse,
    tags=["Documents"],
    summary="Reindex an existing document",
)
async def reindex_document(document_id: str) -> UploadResponse:
    """
    Delete and re-index a document using its saved source file on disk.
    This parses the file and re-adds its text chunks into ChromaDB.
    """
    if document_id not in _document_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    record = _document_registry[document_id]
    filename = record.filename
    save_path = settings.data_path / f"{document_id}_{filename}"

    if not save_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source file for '{filename}' is missing on disk.",
        )

    record.status = DocumentStatus.PROCESSING
    try:
        # Delete from vector store first
        vector_store = get_vector_store()
        vector_store.delete_by_document_id(document_id)

        # Reprocess and index
        processor = DocumentProcessor()
        documents, chunk_metas = processor.process(
            path=save_path, document_id=document_id
        )

        vector_store.add_documents(documents, chunk_metas)

        # Refresh BM25 index after reindexing
        retriever = get_retriever()
        retriever.refresh_bm25_index()

        # Update registry record
        from datetime import datetime
        num_pages = max((m.page or 1) for m in chunk_metas) if chunk_metas else None
        record.status = DocumentStatus.INDEXED
        record.num_chunks = len(documents)
        record.num_pages = num_pages
        record.indexed_at = datetime.utcnow()

        logger.info(
            "Document reindexed",
            extra={
                "file_name": filename,
                "document_id": document_id,
                "num_chunks": len(documents),
            },
        )

        return UploadResponse(
            document_id=document_id,
            filename=filename,
            num_chunks=len(documents),
            num_pages=num_pages,
            status=DocumentStatus.INDEXED,
            message=f"Successfully reindexed {len(documents)} chunks from '{filename}'.",
        )

    except Exception as exc:
        record.status = DocumentStatus.FAILED
        record.error_message = str(exc)
        logger.error(
            "Document reindexing failed",
            extra={"file_name": filename, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess document: {exc}",
        )


# ── Analytics endpoint ─────────────────────────────────────────────────────────

@app.get(
    "/analytics",
    tags=["Analytics"],
    summary="Aggregated retrieval analytics",
)
async def get_analytics() -> dict:
    """
    Return aggregated analytics: latency statistics, source usage,
    agent routing distribution, and retrieval pipeline funnel stats.
    """
    if not _retrieval_metrics:
        return {"message": "No queries processed yet.", "metrics": []}

    total_queries = len(_retrieval_metrics)
    avg_total_ms = sum(m.total_latency_ms for m in _retrieval_metrics) / total_queries
    avg_retrieval_ms = sum(m.retrieval_latency_ms for m in _retrieval_metrics) / total_queries
    avg_vector_ms = sum(m.vector_search_latency_ms for m in _retrieval_metrics) / total_queries
    avg_bm25_ms = sum(m.bm25_search_latency_ms for m in _retrieval_metrics) / total_queries
    avg_rrf_ms = sum(m.rrf_fusion_latency_ms for m in _retrieval_metrics) / total_queries
    avg_reranking_ms = sum(
        m.reranking_latency_ms or 0.0 for m in _retrieval_metrics
    ) / total_queries
    avg_llm_ms = sum(
        m.llm_latency_ms or 0.0 for m in _retrieval_metrics
    ) / total_queries

    agent_counts: dict[str, int] = {}
    all_sources: list[str] = []
    for m in _retrieval_metrics:
        agent_counts[m.agent_type.value] = agent_counts.get(m.agent_type.value, 0) + 1
        all_sources.extend(m.sources_used)

    source_freq: dict[str, int] = {}
    for src in all_sources:
        source_freq[src] = source_freq.get(src, 0) + 1

    # Retrieval funnel averages
    avg_vector_hits = sum(m.num_vector_results for m in _retrieval_metrics) / total_queries
    avg_bm25_hits = sum(m.num_bm25_results for m in _retrieval_metrics) / total_queries
    avg_retrieved = sum(m.num_retrieved for m in _retrieval_metrics) / total_queries
    avg_reranked = sum(m.num_reranked for m in _retrieval_metrics) / total_queries

    # Daily query, token and cost trends
    from datetime import datetime, timezone
    today_date = datetime.now(timezone.utc).date()
    
    daily_stats = {}
    for m in _retrieval_metrics:
        d_str = m.timestamp.strftime("%Y-%m-%d") if isinstance(m.timestamp, datetime) else str(m.timestamp)[:10]
        if d_str not in daily_stats:
            daily_stats[d_str] = {"queries": 0, "tokens": 0, "cost": 0.0}
        daily_stats[d_str]["queries"] += 1
        daily_stats[d_str]["tokens"] += getattr(m, "total_tokens", 0)
        daily_stats[d_str]["cost"] += getattr(m, "cost_usd", 0.0)
    
    sorted_daily = sorted(daily_stats.items())
    daily_trend = [
        {
            "date": k, 
            "queries": v["queries"], 
            "tokens": v["tokens"], 
            "cost": round(v["cost"], 6)
        } for k, v in sorted_daily
    ]

    queries_today = daily_stats.get(today_date.strftime("%Y-%m-%d"), {}).get("queries", 0)

    total_prompt = sum(m.prompt_tokens for m in _retrieval_metrics)
    total_completion = sum(m.completion_tokens for m in _retrieval_metrics)
    total_tokens = sum(m.total_tokens for m in _retrieval_metrics)
    total_cost = sum(m.cost_usd for m in _retrieval_metrics)

    avg_prompt = total_prompt / total_queries
    avg_completion = total_completion / total_queries
    avg_total_tokens = total_tokens / total_queries
    avg_cost = total_cost / total_queries

    # Document chunk distribution
    doc_chunk_dist = {
        doc_rec.filename: doc_rec.num_chunks
        for doc_rec in _document_registry.values()
    }

    return {
        "total_queries": total_queries,
        "queries_today": queries_today,
        # ── Latency summary ──────────────────────────────────────
        "avg_total_latency_ms": round(avg_total_ms, 2),
        "avg_retrieval_latency_ms": round(avg_retrieval_ms, 2),
        "avg_vector_search_ms": round(avg_vector_ms, 2),
        "avg_bm25_search_ms": round(avg_bm25_ms, 2),
        "avg_rrf_fusion_ms": round(avg_rrf_ms, 2),
        "avg_reranking_ms": round(avg_reranking_ms, 2),
        "avg_llm_ms": round(avg_llm_ms, 2),
        # ── Token & Cost summary ─────────────────────────────────
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "avg_prompt_tokens": round(avg_prompt, 2),
        "avg_completion_tokens": round(avg_completion, 2),
        "avg_total_tokens": round(avg_total_tokens, 2),
        "avg_cost_usd": round(avg_cost, 6),
        # ── Funnel summary ───────────────────────────────────────
        "avg_vector_hits": round(avg_vector_hits, 1),
        "avg_bm25_hits": round(avg_bm25_hits, 1),
        "avg_retrieved": round(avg_retrieved, 1),
        "avg_reranked": round(avg_reranked, 1),
        # ── Distribution ─────────────────────────────────────────
        "agent_distribution": agent_counts,
        "top_sources": sorted(source_freq.items(), key=lambda x: x[1], reverse=True)[:10],
        "document_chunk_distribution": doc_chunk_dist,
        "recent_metrics": [m.model_dump() for m in _retrieval_metrics[-20:]],
        "daily_trend": daily_trend,
    }



# ── Dedicated retrieval-metrics endpoint ───────────────────────────────────────

@app.get(
    "/retrieval-metrics",
    tags=["Analytics"],
    summary="Per-query retrieval pipeline metrics",
)
async def get_retrieval_metrics(limit: int = 50) -> dict:
    """
    Return detailed per-query retrieval pipeline metrics for the observability dashboard.

    Includes stage-by-stage latency, chunk counts, and score distributions for
    vector search, BM25, RRF fusion, and cross-encoder reranking.

    Args:
        limit: Max number of recent metrics to return (default 50).
    """
    if not _retrieval_metrics:
        return {"message": "No queries processed yet.", "metrics": []}

    recent = _retrieval_metrics[-limit:]
    return {
        "total_logged": len(_retrieval_metrics),
        "returned": len(recent),
        "metrics": [m.model_dump() for m in recent],
    }


# ── LangGraph visualisation endpoint ──────────────────────────────────────────

@app.get(
    "/graph",
    tags=["System"],
    summary="Get LangGraph Mermaid representation",
)
async def get_graph() -> dict:
    """
    Return the Mermaid diagram source code of the compiled LangGraph workflow.
    """
    orchestrator = get_orchestrator()
    mermaid_code = orchestrator.get_graph_mermaid()
    return {"mermaid": mermaid_code}




# ── Reload configuration ──────────────────────────────────────────────────────

@app.post(
    "/reload",
    tags=["System"],
    summary="Reload configuration and reinitialise all services",
)
async def reload_config() -> dict:
    """
    Reload settings from the `.env` file and reinitialise all singletons.

    Call this after updating `GOOGLE_API_KEY` or any other setting in `.env`
    so the new values take effect **without restarting the server**.
    """
    import app.utils.config as _config_mod
    import app.rag.embeddings as _emb_mod
    import app.rag.vector_store as _vs_mod
    import app.rag.retriever as _ret_mod
    import app.agents.rag_agent as _rag_mod
    import app.agents.router as _router_mod
    import app.agents.web_agent as _web_mod
    import app.agents.memory_agent as _mem_mod
    import app.agents.graph as _graph_mod

    # Clear the settings LRU cache so .env is re-read
    _config_mod.get_settings.cache_clear()

    # Reset all module-level singletons
    _emb_mod._embedding_service = None
    _vs_mod._vector_store = None
    _ret_mod._retriever = None
    _rag_mod._rag_agent = None
    _router_mod._router = None
    _web_mod._web_agent = None
    _mem_mod._memory_agent = None
    _graph_mod._orchestrator = None

    # Reinitialise eagerly so startup failures surface immediately
    try:
        new_settings = _config_mod.get_settings()
        _ = get_vector_store()
        _ = get_retriever()
        _ = get_orchestrator()
        logger.info(
            "Configuration reloaded",
            extra={"gemini_model": new_settings.gemini_model, "embedding_model": new_settings.embedding_model},
        )
        return {
            "status": "reloaded",
            "gemini_model": new_settings.gemini_model,
            "embedding_model": new_settings.embedding_model,
        }
    except Exception as exc:
        logger.error("Reload failed", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reload failed: {exc}",
        )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
