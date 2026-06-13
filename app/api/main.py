"""
Enterprise Agentic RAG Assistant
FastAPI backend — document management and chat endpoints.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.graph import AgentOrchestrator, get_orchestrator
from app.models.schemas import (
    AgentType,
    BenchmarkProviderResult,
    BenchmarkRun,
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
    WorkflowNodeType,
    WorkflowNodeDef,
    WorkflowEdgeDef,
    WorkflowDefinition,
    WorkflowExecutionStep,
    WorkflowExecutionResult,
)
from app.rag.document_processor import DocumentProcessor
from app.rag.retriever import _compute_score_distribution, get_retriever
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

# ── Benchmark store ────────────────────────────────────────────────────────────
_benchmark_runs: list[BenchmarkRun] = []
BENCHMARK_FILE = settings.data_path / "benchmark_runs.jsonl"

def _load_benchmark_history() -> list[BenchmarkRun]:
    runs: list[BenchmarkRun] = []
    if BENCHMARK_FILE.exists():
        try:
            with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        runs.append(BenchmarkRun.model_validate_json(stripped))
        except Exception as exc:
            logger.error("Failed to load benchmark history", extra={"error": str(exc)}, exc_info=True)
    return runs

def _persist_benchmark_run(run: BenchmarkRun) -> None:
    try:
        BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BENCHMARK_FILE, "a", encoding="utf-8") as f:
            f.write(run.model_dump_json() + "\n")
    except Exception as exc:
        logger.error("Failed to persist benchmark run", extra={"error": str(exc)}, exc_info=True)

def _load_persisted_metrics() -> list[RetrievalMetric]:
    metrics = []
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        metrics.append(RetrievalMetric.model_validate_json(stripped))
            logger.info(
                "Persisted metrics loaded",
                extra={"count": len(metrics), "file": str(METRICS_FILE)},
            )
        except Exception as exc:
            logger.error("Failed to load persisted metrics", extra={"error": str(exc)}, exc_info=True)
    return metrics

def _persist_metric(metric: RetrievalMetric) -> None:
    try:
        # Ensure parent directory exists
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(metric.model_dump_json() + "\n")
    except Exception as exc:
        logger.error("Failed to persist metric", extra={"error": str(exc)}, exc_info=True)


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
                created_at=datetime.now(timezone.utc),
            )
        logger.info(
            "Document registry rebuilt",
            extra={"count": len(_document_registry)},
        )
    except Exception as exc:
        logger.error(
            "Failed to rebuild document registry",
            extra={"error": str(exc)},
            exc_info=True,
        )


# ── Application lifespan ─────────────────────────────────────────────────────────

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
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

_cors_origins = (
    [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    if settings.allowed_origins != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate limiting ──────────────────────────────────────────────────────────────

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    _limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    _RATE_LIMITING_ENABLED = True
    logger.info("Rate limiting enabled via slowapi")
except ImportError:
    _RATE_LIMITING_ENABLED = False
    logger.warning("slowapi not installed — rate limiting disabled.")


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
        version=settings.api_version,
        vector_store="chromadb",
        embedding_model=active_emb,
        llm_model=active_llm,
        llm_provider=settings.llm_provider,
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
        # ── Save uploaded file ──────────────────────────────────────────────
        content = await file.read()

        # ── File size limit ─────────────────────────────────────────────────
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {settings.max_upload_size_mb} MB.",
            )

        # ── MIME-type validation ──────────────────────────────────────────────
        try:
            import magic
            detected_mime = magic.from_buffer(content[:2048], mime=True)
            _ALLOWED_MIMES = {
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
            }
            if detected_mime not in _ALLOWED_MIMES:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=(
                        f"Detected MIME type '{detected_mime}' is not allowed. "
                        f"Allowed types: PDF, DOCX, TXT."
                    ),
                )
        except ImportError:
            # python-magic not available; fall back to extension-only check
            logger.warning("python-magic not available; skipping MIME-type validation")
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
        from datetime import datetime, timezone

        num_pages = max((m.page or 1) for m in chunk_metas) if chunk_metas else None
        record.status = DocumentStatus.INDEXED
        record.num_chunks = len(documents)
        record.num_pages = num_pages
        record.indexed_at = datetime.now(timezone.utc)

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


# ── Career Intelligence Analyzer ──────────────────────────────────────────────

_ANALYSIS_SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) and Career Intelligence Agent.
Compare the provided Resume text and Job Description text.

Extract the following details and perform a comparison:
1. Skills present in the resume.
2. Projects mentioned in the resume.
3. Education history from the resume.
4. Experience history from the resume.
5. Job Description requirements (skills, experience, education).
6. Strengths of the candidate relative to the JD.
7. Weaknesses of the candidate relative to the JD.
8. Suggestions for improvement to make the resume stand out or prepare for the interview.

Perform scoring:
- Match Score (0 to 100) based on overall fit.
- Skill Match % (0 to 100) based on key technologies/skills match.
- Project Match % (0 to 100) based on relevance of projects.
- Experience Match % (0 to 100) based on job history alignment.
- Education Match % (0 to 100) based on degree/major requirements match.
- Keyword Match % (0 to 100) based on target vocabulary.
- Formatting Score % (0 to 100) based on resume layout (clarity, section divisions, lack of parsing errors).

Perform missing skills classification:
- Critical (must-have skills missing in the resume but highly emphasized in the JD).
- Recommended (should-have skills missing in the resume).
- Optional (nice-to-have skills missing in the resume).

Perform keyword analysis:
- Extract top keywords from the JD (minimum 4).
- Extract top keywords from the Resume (minimum 4).
- Identify missing keywords (minimum 3).
- Calculate keyword coverage % (0 to 100).

Perform interview readiness assessment:
- Calculate an Interview Readiness Score (0 to 100).
- Assign a status: "Likely Shortlisted" (score 75+), "Borderline" (score 60-74), or "Needs Improvement" (score <60).

CRITICAL GUIDELINES FOR EXTRACTION:
- You MUST analyze the candidate's actual Resume text and Job Description text. Do NOT use the example values from the JSON template below.
- "extracted_education": Extract the candidate's actual highest degree(s), school/university, major(s), and graduation year from their Resume (e.g., "B.Tech in Electronics and Communication Engineering from Indian Institute of Information Technology Dharwad (2023 - 2027)"). Do NOT copy "MS in CS from Stanford University". If not found, output "Not specified in resume".
- "extracted_experience": Extract the candidate's actual professional work history or a summary of their career background from their Resume (e.g., "Intern at X", "Freelance developer", or "No formal experience" if they only have academic projects). Do NOT copy "3 years as a Software Engineer at Google". If not found, output "Not specified in resume".
- All scores, missing skills, projects, and insights must be derived dynamically from the real input text.

You MUST respond with a single valid JSON object containing the exact keys listed below:
{
  "match_score": 84,
  "skill_match_pct": 88,
  "project_match_pct": 82,
  "experience_match_pct": 79,
  "education_match_pct": 95,
  "keyword_match_pct": 76,
  "formatting_score": 90,
  "extracted_skills": [
    {"name": "Python", "present": true},
    {"name": "LangGraph", "present": false}
  ],
  "extracted_projects": ["Project A: built a RAG app...", "Project B: ..."],
  "extracted_education": "<EXTRACT AND INSERT ACTUAL EDUCATION FROM RESUME TEXT HERE>",
  "extracted_experience": "<EXTRACT AND INSERT ACTUAL EXPERIENCE/WORK HISTORY FROM RESUME TEXT HERE>",
  "jd_requirements": ["Degree in CS", "Experience with RAG", "Knowledge of ChromaDB"],
  "missing_skills_categorized": {
    "critical": ["LangGraph", "Kubernetes"],
    "recommended": ["CI/CD", "AWS"],
    "optional": ["Docker", "Git"]
  },
  "keyword_analysis": {
    "top_jd_keywords": [{"text": "Kubernetes", "value": 8}, {"text": "LangGraph", "value": 6}],
    "top_resume_keywords": [{"text": "Python", "value": 10}, {"text": "RAG", "value": 5}],
    "missing_keywords": ["Kubernetes", "CI/CD"],
    "keyword_coverage_pct": 76
  },
  "recruiter_insights": {
    "strengths": ["Strong Python experience", "Relevant AI projects"],
    "weaknesses": ["Missing deployment experience", "Limited cloud keywords"],
    "improvement_suggestions": ["Add Kubernetes setup to Project A", "Study LangGraph routing schemas"]
  },
  "interview_readiness": {
    "score": 78,
    "status": "Likely Shortlisted"
  }
}

Respond ONLY with the raw JSON. Do not include markdown code fences, notes, or explanations outside the JSON."""


@app.post(
    "/analyze-resume",
    tags=["Career Intelligence"],
    summary="Analyze resume against job description",
)
async def analyze_resume(
    resume: UploadFile = File(...),
    jd: UploadFile = File(...)
) -> dict:
    """
    Compare a candidate's resume PDF against a job description PDF.
    Extracts skills, education, experience, projects, and calculates match scores.
    """
    import json
    from app.utils.pdf_extractor import extract_text_from_pdf
    from app.utils.llm_factory import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    # Validate file extensions
    for f in (resume, jd):
        ext = Path(f.filename or "").suffix.lower().lstrip(".")
        if ext != "pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Only PDF files are supported. Uploaded file is '.{ext}'"
            )

    try:
        # Extract text from both files
        resume_bytes = await resume.read()
        jd_bytes = await jd.read()
        
        resume_text = extract_text_from_pdf(resume_bytes)
        jd_text = extract_text_from_pdf(jd_bytes)

        if not resume_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract readable text from Resume PDF."
            )
        if not jd_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract readable text from Job Description PDF."
            )

        # Assemble prompt for LLM comparison
        prompt = f"RESUME TEXT:\n{resume_text}\n\nJOB DESCRIPTION TEXT:\n{jd_text}"
        messages = [
            SystemMessage(content=_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        llm = get_llm(temperature=0.1)
        response = llm.invoke(messages)
        content = response.content.strip()

        # Clean code fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        analysis_result = json.loads(content)
        return analysis_result

    except Exception as exc:
        logger.error("Resume analysis failed", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume analysis comparison failed: {exc}"
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

        # Rebuild BM25 index after deletion (non-fatal if it fails)
        retriever = get_retriever()
        try:
            retriever.refresh_bm25_index()
        except Exception as bm25_exc:
            logger.error(
                "BM25 index refresh failed after document deletion",
                extra={"document_id": document_id, "error": str(bm25_exc)},
                exc_info=True,
            )

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
        from datetime import datetime, timezone
        num_pages = max((m.page or 1) for m in chunk_metas) if chunk_metas else None
        record.status = DocumentStatus.INDEXED
        record.num_chunks = len(documents)
        record.num_pages = num_pages
        record.indexed_at = datetime.now(timezone.utc)

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


# ── Extended Analytics endpoint ────────────────────────────────────────────────

@app.get(
    "/analytics/extended",
    tags=["Analytics"],
    summary="Extended analytics: provider, memory, document, and retrieval-quality metrics",
)
async def get_extended_analytics() -> dict:
    """
    Return additional analytic dimensions not in /analytics:
    - Provider usage distribution (derived from agent + LLM config)
    - Memory metrics (total stored, by type, growth over time)
    - Document metrics (total docs, total chunks, file-type breakdown)
    - Retrieval success rate (queries where chunks > 0)
    - Query length distribution
    - Hourly query volume heatmap
    - Session engagement depth
    """
    from datetime import datetime, timezone
    from app.rag.memory_store import get_memory_store

    out: dict = {}

    # ── 1. Provider usage ─────────────────────────────────────────────────────
    # We tag provider by the active LLM setting; stored per-metric via agent_type
    llm_provider = settings.llm_provider.lower()
    total_q = len(_retrieval_metrics)
    out["llm_provider"] = llm_provider
    out["total_queries"] = total_q

    # Build a simple provider count (all queries used the same configured provider)
    out["provider_usage"] = {llm_provider: total_q} if total_q else {}

    # ── 2. Agent usage ────────────────────────────────────────────────────────
    agent_counts: dict[str, int] = {}
    for m in _retrieval_metrics:
        k = m.agent_type.value
        agent_counts[k] = agent_counts.get(k, 0) + 1
    out["agent_distribution"] = agent_counts
    out["most_used_agent"] = max(agent_counts, key=agent_counts.get) if agent_counts else "N/A"

    # ── 3. Latency summary ────────────────────────────────────────────────────
    if total_q:
        out["avg_total_latency_ms"]   = round(sum(m.total_latency_ms for m in _retrieval_metrics) / total_q, 2)
        out["avg_retrieval_ms"]       = round(sum(m.retrieval_latency_ms for m in _retrieval_metrics) / total_q, 2)
        out["avg_reranking_ms"]       = round(sum(m.reranking_latency_ms or 0 for m in _retrieval_metrics) / total_q, 2)
        out["avg_llm_ms"]             = round(sum(m.llm_latency_ms or 0 for m in _retrieval_metrics) / total_q, 2)
        out["p95_total_latency_ms"]   = 0.0
        sorted_lats = sorted(m.total_latency_ms for m in _retrieval_metrics)
        if sorted_lats:
            idx = int(0.95 * len(sorted_lats))
            out["p95_total_latency_ms"] = round(sorted_lats[min(idx, len(sorted_lats)-1)], 2)
    else:
        out.update({k: 0.0 for k in (
            "avg_total_latency_ms", "avg_retrieval_ms",
            "avg_reranking_ms", "avg_llm_ms", "p95_total_latency_ms"
        )})

    # ── 4. Retrieval quality metrics ──────────────────────────────────────────
    if total_q:
        successful = sum(1 for m in _retrieval_metrics if m.num_reranked > 0)
        out["retrieval_success_rate"]  = round(successful / total_q * 100, 1)
        out["avg_chunks_retrieved"]    = round(sum(m.num_retrieved for m in _retrieval_metrics) / total_q, 1)
        out["avg_chunks_reranked"]     = round(sum(m.num_reranked for m in _retrieval_metrics) / total_q, 1)
        out["avg_vector_hits"]         = round(sum(m.num_vector_results for m in _retrieval_metrics) / total_q, 1)
        out["avg_bm25_hits"]           = round(sum(m.num_bm25_results for m in _retrieval_metrics) / total_q, 1)
    else:
        out.update({k: 0.0 for k in (
            "retrieval_success_rate", "avg_chunks_retrieved",
            "avg_chunks_reranked", "avg_vector_hits", "avg_bm25_hits"
        )})

    # ── 5. Token & cost ───────────────────────────────────────────────────────
    total_prompt     = sum(m.prompt_tokens for m in _retrieval_metrics)
    total_completion = sum(m.completion_tokens for m in _retrieval_metrics)
    total_tokens     = sum(m.total_tokens for m in _retrieval_metrics)
    total_cost       = sum(m.cost_usd for m in _retrieval_metrics)
    out["total_prompt_tokens"]     = total_prompt
    out["total_completion_tokens"] = total_completion
    out["total_tokens"]            = total_tokens
    out["total_cost_usd"]          = round(total_cost, 6)
    out["avg_cost_usd"]            = round(total_cost / total_q, 8) if total_q else 0.0
    out["avg_total_tokens"]        = round(total_tokens / total_q, 1) if total_q else 0.0

    # ── 6. Query length distribution ─────────────────────────────────────────
    if _retrieval_metrics:
        qlens = [m.query_length for m in _retrieval_metrics]
        out["avg_query_length"]  = round(sum(qlens) / len(qlens), 1)
        out["max_query_length"]  = max(qlens)
        out["min_query_length"]  = min(qlens)
        # Histogram buckets: short(<50) / medium(50-150) / long(>150)
        out["query_length_distribution"] = {
            "short (<50 chars)":   sum(1 for l in qlens if l < 50),
            "medium (50–150)":     sum(1 for l in qlens if 50 <= l < 150),
            "long (>150 chars)":   sum(1 for l in qlens if l >= 150),
        }
    else:
        out["avg_query_length"] = out["max_query_length"] = out["min_query_length"] = 0
        out["query_length_distribution"] = {}

    # ── 7. Hourly query volume heatmap (0–23) ────────────────────────────────
    hourly: dict[int, int] = {h: 0 for h in range(24)}
    for m in _retrieval_metrics:
        try:
            h = int(m.timestamp.strftime("%H"))
            hourly[h] = hourly.get(h, 0) + 1
        except Exception:
            pass
    out["hourly_query_counts"] = [{"hour": h, "count": hourly[h]} for h in range(24)]

    # ── 8. Daily trend ────────────────────────────────────────────────────────
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_stats: dict[str, dict] = {}
    for m in _retrieval_metrics:
        d = m.timestamp.strftime("%Y-%m-%d") if isinstance(m.timestamp, datetime) else str(m.timestamp)[:10]
        if d not in daily_stats:
            daily_stats[d] = {"queries": 0, "tokens": 0, "cost": 0.0, "latency_sum": 0.0}
        daily_stats[d]["queries"]     += 1
        daily_stats[d]["tokens"]      += m.total_tokens
        daily_stats[d]["cost"]        += m.cost_usd
        daily_stats[d]["latency_sum"] += m.total_latency_ms
    out["daily_trend"] = [
        {
            "date":        d,
            "queries":     v["queries"],
            "tokens":      v["tokens"],
            "cost":        round(v["cost"], 6),
            "avg_latency": round(v["latency_sum"] / v["queries"], 1) if v["queries"] else 0.0,
        }
        for d, v in sorted(daily_stats.items())
    ]
    out["queries_today"] = daily_stats.get(today_str, {}).get("queries", 0)

    # ── 9. Top referenced sources ─────────────────────────────────────────────
    source_freq: dict[str, int] = {}
    for m in _retrieval_metrics:
        for src in m.sources_used:
            source_freq[src] = source_freq.get(src, 0) + 1
    out["top_sources"] = sorted(source_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── 10. Memory metrics ────────────────────────────────────────────────────
    try:
        store   = get_memory_store()
        all_mem = store.list_all_memories()
        mem_by_type: dict[str, int] = {}
        for mem in all_mem:
            t = mem.get("memory_type", "unknown")
            mem_by_type[t] = mem_by_type.get(t, 0) + 1
        out["memory_metrics"] = {
            "total_memories":    len(all_mem),
            "by_type":           mem_by_type,
            "facts":             mem_by_type.get("fact", 0),
            "preferences":       mem_by_type.get("preference", 0),
            "summaries":         mem_by_type.get("summary", 0),
        }
    except Exception as exc:
        logger.warning(f"Failed to load memory metrics: {exc}")
        out["memory_metrics"] = {"total_memories": 0, "by_type": {}, "facts": 0, "preferences": 0, "summaries": 0}

    # ── 11. Document metrics ──────────────────────────────────────────────────
    docs      = list(_document_registry.values())
    file_type_dist: dict[str, int] = {}
    total_chunks  = 0
    total_pages   = 0
    for doc in docs:
        ft = doc.file_type.value if hasattr(doc.file_type, "value") else str(doc.file_type)
        file_type_dist[ft] = file_type_dist.get(ft, 0) + 1
        total_chunks += doc.num_chunks
        total_pages  += doc.num_pages or 0
    out["document_metrics"] = {
        "total_documents":       len(docs),
        "total_chunks_indexed":  total_chunks,
        "total_pages_indexed":   total_pages,
        "avg_chunks_per_doc":    round(total_chunks / len(docs), 1) if docs else 0.0,
        "file_type_distribution": file_type_dist,
        "document_chunk_distribution": {
            d.filename: d.num_chunks for d in docs
        },
    }

    # ── 12. Recent metrics table (last 20) ────────────────────────────────────
    out["recent_metrics"] = [m.model_dump() for m in _retrieval_metrics[-20:]]

    return out


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


# ── Benchmark Endpoints ────────────────────────────────────────────────────────

_BENCHMARK_PROMPT_TEMPLATE = """You are an expert AI assistant. Answer the following question clearly and concisely.

{context_block}QUESTION:
{query}

ANSWER:"""

_FAITHFULNESS_PROMPT = """
You are an evaluator measuring the faithfulness and relevance of an AI response against the provided reference context.

Context:
{context}

AI Response:
{response}

Evaluate the response faithfulness on a scale of 0 to 100 where:
- 100 = fully faithful, every claim grounded in the context
- 0 = completely unfaithful, fabricated or unrelated

Respond with ONLY a JSON object:
{{"score": <integer 0-100>, "reasoning": "<one sentence explanation>"}}"""


@app.post(
    "/benchmark",
    tags=["Benchmark"],
    summary="Run a prompt across all LLM providers and compare results",
)
async def run_benchmark(
    query: str,
    use_rag: bool = False,
    temperature: float = 0.1,
) -> dict:
    """
    Execute a prompt concurrently across Ollama, Groq, and Gemini.
    Measures latency, token usage, cost, response length, and retrieval accuracy.
    Returns a leaderboard-ready result dict plus full provider details.
    """
    import asyncio
    import json
    import re
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.utils.llm_factory import get_provider_llm, extract_token_usage, calculate_provider_cost
    from app.utils.config import get_settings as _get_settings

    cfg = _get_settings()

    # ── 1. Optional: retrieve RAG context ─────────────────────────────────────
    context_text = ""
    context_block = ""
    if use_rag:
        try:
            retriever = get_retriever()
            chunks = retriever.retrieve(query=query, top_k=5)
            if chunks:
                parts = []
                for i, c in enumerate(chunks, 1):
                    parts.append(f"[{i}] {c.metadata.source}: {c.content[:600]}")
                context_text = "\n".join(parts)
                context_block = f"CONTEXT FROM DOCUMENTS:\n{context_text}\n\n"
        except Exception as exc:
            logger.warning(f"RAG retrieval failed during benchmark: {exc}")

    prompt_text = _BENCHMARK_PROMPT_TEMPLATE.format(
        context_block=context_block, query=query
    )

    # ── 2. Provider configs ────────────────────────────────────────────────────
    provider_configs = [
        ("gemini",  cfg.gemini_model),
        ("groq",    cfg.groq_model),
        ("ollama",  cfg.ollama_model),
    ]

    # ── 3. Concurrent invocation via asyncio ──────────────────────────────────
    async def call_provider(provider: str, model: str) -> BenchmarkProviderResult:
        loop = asyncio.get_running_loop()
        try:
            llm = await loop.run_in_executor(
                None, lambda: get_provider_llm(provider, temperature=temperature)
            )
            messages = [
                SystemMessage(content="You are a helpful AI assistant."),
                HumanMessage(content=prompt_text),
            ]
            t0 = time.perf_counter()
            response = await loop.run_in_executor(None, lambda: llm.invoke(messages))
            latency_s = time.perf_counter() - t0

            content = response.content or ""
            p_tok, c_tok, t_tok = extract_token_usage(response)
            # Fallback estimate when provider returns no token counts
            if t_tok == 0:
                estimated = max(1, int((len(prompt_text) + len(content)) / 4))
                p_tok = int(len(prompt_text) / 4)
                c_tok = estimated - p_tok
                t_tok = estimated

            cost = calculate_provider_cost(provider, p_tok, c_tok)
            words = len(content.split())

            return BenchmarkProviderResult(
                provider=provider,
                model=model,
                response=content,
                latency_s=round(latency_s, 3),
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                total_tokens=t_tok,
                cost_usd=round(cost, 8),
                response_length_chars=len(content),
                response_length_words=words,
            )
        except Exception as exc:
            return BenchmarkProviderResult(
                provider=provider,
                model=model,
                response="",
                latency_s=0.0,
                error=str(exc),
            )

    tasks = [call_provider(p, m) for p, m in provider_configs]
    raw_results: list[BenchmarkProviderResult] = await asyncio.gather(*tasks)
    results_map: dict[str, BenchmarkProviderResult] = {r.provider: r for r in raw_results}

    # ── 4. Retrieval Accuracy via LLM faithfulness evaluator ──────────────────
    eval_context = context_text if use_rag and context_text else query

    async def evaluate_faithfulness(res: BenchmarkProviderResult) -> None:
        if res.error or not res.response:
            res.retrieval_accuracy = 0.0
            res.evaluation_reasoning = "Provider returned an error — faithfulness N/A."
            return
        loop = asyncio.get_running_loop()
        try:
            eval_llm = await loop.run_in_executor(
                None, lambda: get_provider_llm(cfg.llm_provider.lower(), temperature=0.0)
            )
            eval_prompt = _FAITHFULNESS_PROMPT.format(
                context=eval_context[:3000], response=res.response[:2000]
            )
            eval_resp = await loop.run_in_executor(
                None, lambda: eval_llm.invoke([HumanMessage(content=eval_prompt)])
            )
            raw = eval_resp.content.strip()
            # Extract JSON from possible code-fence wrapping
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            if m:
                data = json.loads(m.group())
                res.retrieval_accuracy = float(data.get("score", 80.0))
                res.evaluation_reasoning = data.get("reasoning", "")
            else:
                res.retrieval_accuracy = 80.0
                res.evaluation_reasoning = "Could not parse evaluator output."
        except Exception as exc:
            logger.warning(f"Faithfulness eval failed for {res.provider}: {exc}")
            res.retrieval_accuracy = 75.0
            res.evaluation_reasoning = f"Evaluation error: {exc}"

    await asyncio.gather(*[evaluate_faithfulness(r) for r in raw_results])

    # ── 5. Composite score ────────────────────────────────────────────────────
    # Score = 0.5 * accuracy_norm + 0.3 * speed_norm + 0.2 * cost_efficiency
    active = [r for r in raw_results if not r.error]
    if active:
        max_lat = max(r.latency_s for r in active) or 1.0
        max_cost = max(r.cost_usd for r in active) or 1e-9
        for r in active:
            speed_score    = max(0, (1 - r.latency_s / max_lat)) * 100
            cost_score     = max(0, (1 - r.cost_usd  / max_cost)) * 100
            r.composite_score = round(
                0.5 * r.retrieval_accuracy + 0.3 * speed_score + 0.2 * cost_score, 2
            )

    # ── 6. Persist and return ─────────────────────────────────────────────────
    run = BenchmarkRun(
        query=query,
        context_retrieved=context_text,
        use_rag=use_rag,
        results=results_map,
    )
    _benchmark_runs.append(run)
    _persist_benchmark_run(run)

    return run.model_dump(mode="json")


@app.get(
    "/benchmark/history",
    tags=["Benchmark"],
    summary="Retrieve all stored benchmark run history",
)
async def get_benchmark_history(limit: int = 50) -> dict:
    """
    Return the most recent benchmark runs from the persistent JSONL store.
    """
    history = _load_benchmark_history()
    return {
        "total": len(history),
        "runs": [r.model_dump(mode="json") for r in history[-limit:]],
    }


@app.delete(
    "/benchmark/history",
    tags=["Benchmark"],
    summary="Clear all stored benchmark history",
)
async def clear_benchmark_history() -> dict:
    """
    Delete the benchmark_runs.jsonl file and reset the in-memory store.
    """
    global _benchmark_runs
    _benchmark_runs = []
    try:
        if BENCHMARK_FILE.exists():
            BENCHMARK_FILE.unlink()
        return {"status": "cleared", "message": "Benchmark history cleared successfully."}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear benchmark history: {exc}",
        )


# ── Visual Workflow Endpoints ──────────────────────────────────────────────────

WORKFLOWS_DIR = settings.data_path / "workflows"
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

@app.post(
    "/workflows",
    tags=["Workflow Builder"],
    summary="Save or update a workflow definition",
)
async def save_workflow(workflow: WorkflowDefinition) -> dict:
    """Save a workflow definition to disk as a JSON file."""
    try:
        from datetime import datetime, timezone
        workflow.updated_at = datetime.now(timezone.utc)
        filepath = WORKFLOWS_DIR / f"{workflow.workflow_id}.json"
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(workflow.model_dump_json(indent=2))
        logger.info(
            "Workflow saved",
            extra={"name": workflow.name, "workflow_id": workflow.workflow_id},
        )
        return {"status": "saved", "workflow_id": workflow.workflow_id}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save workflow: {exc}",
        )

@app.get(
    "/workflows",
    tags=["Workflow Builder"],
    summary="List all saved workflow definitions",
)
async def list_workflows() -> list[dict]:
    """List all saved workflows from disk."""
    import json
    workflows = []
    try:
        for p in WORKFLOWS_DIR.glob("*.json"):
            async with aiofiles.open(p, "r", encoding="utf-8") as f:
                content = await f.read()
                workflows.append(json.loads(content))
        # Sort by updated_at desc
        workflows.sort(key=lambda w: w.get("updated_at", ""), reverse=True)
        return workflows
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {exc}",
        )

@app.get(
    "/workflows/{workflow_id}",
    tags=["Workflow Builder"],
    summary="Get a specific workflow definition",
)
async def get_workflow(workflow_id: str) -> dict:
    """Retrieve a specific workflow definition from disk."""
    import json
    filepath = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load workflow: {exc}",
        )

@app.delete(
    "/workflows/{workflow_id}",
    tags=["Workflow Builder"],
    summary="Delete a saved workflow",
)
async def delete_workflow(workflow_id: str) -> dict:
    """Delete a workflow definition and its associated executions."""
    filepath = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    try:
        filepath.unlink()
        # Clean up history if any
        exec_file = WORKFLOWS_DIR / f"executions_{workflow_id}.jsonl"
        if exec_file.exists():
            exec_file.unlink()
        logger.info(f"Deleted workflow {workflow_id}")
        return {"status": "deleted", "workflow_id": workflow_id}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {exc}",
        )

@app.post(
    "/workflows/{workflow_id}/execute",
    tags=["Workflow Builder"],
    summary="Execute a workflow definition against a user query",
)
async def execute_workflow_route(workflow_id: str, query: str) -> dict:
    """Load workflow and execute using workflow_executor."""
    import json
    from app.services.workflow_executor import execute_workflow
    
    filepath = WORKFLOWS_DIR / f"{workflow_id}.json"
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found.",
        )
    
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            content = await f.read()
            workflow = WorkflowDefinition.model_validate_json(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse workflow: {exc}",
        )

    # Execute workflow synchronously in an executor thread
    import asyncio
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: execute_workflow(workflow, query)
        )
        
        # Persist execution history
        exec_file = WORKFLOWS_DIR / f"executions_{workflow_id}.jsonl"
        async with aiofiles.open(exec_file, "a", encoding="utf-8") as f:
            await f.write(result.model_dump_json() + "\n")
            
        return result.model_dump(mode="json")
    except Exception as exc:
        logger.error(f"Workflow execution failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {exc}",
        )

@app.get(
    "/workflows/{workflow_id}/executions",
    tags=["Workflow Builder"],
    summary="Retrieve execution history for a workflow",
)
async def get_workflow_executions(workflow_id: str, limit: int = 50) -> dict:
    """Retrieve list of past execution results for a workflow."""
    import json
    exec_file = WORKFLOWS_DIR / f"executions_{workflow_id}.jsonl"
    executions = []
    if exec_file.exists():
        try:
            async with aiofiles.open(exec_file, "r", encoding="utf-8") as f:
                async for line in f:
                    stripped = line.strip()
                    if stripped:
                        executions.append(json.loads(stripped))
        except Exception as exc:
            logger.error(f"Failed to load executions for {workflow_id}: {exc}")
            
    # Sort descending by completed_at/started_at
    executions.sort(key=lambda e: e.get("started_at", ""), reverse=True)
    return {
        "workflow_id": workflow_id,
        "total": len(executions),
        "executions": executions[:limit],
    }


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
