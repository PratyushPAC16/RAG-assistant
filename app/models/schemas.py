"""
Enterprise Agentic RAG Assistant
Pydantic models (schemas) shared across the entire application.
Covers document metadata, chat messages, API request/response shapes,
agent state, and analytics payloads.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ──────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    """Which agent handled a given query."""

    RAG = "rag"
    WEB = "web"
    MEMORY = "memory"
    HYBRID = "hybrid"


class DocumentStatus(str, Enum):
    """Processing lifecycle of an uploaded document."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class FileType(str, Enum):
    """Supported upload file formats."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


# ── Document Metadata ─────────────────────────────────────────────────────────

class ChunkMetadata(BaseModel):
    """Metadata attached to every text chunk stored in the vector database."""

    source: str = Field(..., description="Original filename, e.g. 'report.pdf'")
    document_name: str = Field(default="", description="Original filename, e.g. 'report.pdf'")
    page: int | None = Field(
        default=None, ge=1, description="1-indexed page number (None for TXT files)"
    )
    file_type: str = Field(default="", description="File format: pdf, docx, txt")
    chunk_id: str = Field(
        default_factory=lambda: f"chunk_{uuid4().hex[:12]}",
        description="Unique chunk identifier",
    )
    document_id: str = Field(..., description="Parent document UUID")
    char_start: int | None = Field(
        default=None, description="Character offset of chunk start in source text"
    )
    char_end: int | None = Field(
        default=None, description="Character offset of chunk end in source text"
    )
    total_chunks: int | None = Field(
        default=None, description="Total chunks in the parent document"
    )

    model_config = {"populate_by_name": True}


class DocumentRecord(BaseModel):
    """Record stored in the application's document registry."""

    document_id: str = Field(
        default_factory=lambda: uuid4().hex, description="Unique document UUID"
    )
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="File format")
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING, description="Processing status"
    )
    num_chunks: int = Field(default=0, ge=0, description="Number of indexed chunks")
    num_pages: int | None = Field(
        default=None, description="Total pages (PDF/DOCX only)"
    )
    file_size_bytes: int = Field(default=0, ge=0, description="File size in bytes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = Field(
        default=None, description="Timestamp when indexing completed"
    )
    error_message: str | None = Field(
        default=None, description="Error details if status is FAILED"
    )


# ── Retrieval & Reranking ─────────────────────────────────────────────────────

class RetrievedChunk(BaseModel):
    """A single text chunk returned from the retrieval pipeline."""

    chunk_id: str
    content: str
    metadata: ChunkMetadata
    semantic_score: float | None = Field(
        default=None, description="Cosine similarity from vector search"
    )
    bm25_score: float | None = Field(
        default=None, description="BM25 relevance score"
    )
    rerank_score: float | None = Field(
        default=None, description="Cross-encoder reranking score"
    )
    final_rank: int | None = Field(
        default=None, description="Rank after reranking (1 = best)"
    )


class SourceCitation(BaseModel):
    """Citation attached to the final answer."""

    document: str = Field(..., description="Source document filename")
    page: int | None = Field(default=None, description="Page number in source document")
    chunk_id: str | None = Field(default=None, description="Chunk identifier")
    relevance_score: float | None = Field(
        default=None, description="Relevance confidence [0–1]"
    )


# ── Chat & Memory ─────────────────────────────────────────────────────────────

class MessageRole(str, Enum):
    """Roles in a conversation turn."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_type: AgentType | None = Field(
        default=None, description="Agent that produced this message"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary extra metadata"
    )


class ConversationMemory(BaseModel):
    """In-memory conversation history for one session."""

    session_id: str = Field(default_factory=lambda: uuid4().hex)
    messages: list[ChatMessage] = Field(default_factory=list)
    max_turns: int = Field(
        default=10, gt=0, description="Maximum number of turns to retain"
    )

    def add_message(self, role: MessageRole, content: str, **kwargs: Any) -> None:
        """Append a message and trim history to *max_turns* most-recent turns."""
        self.messages.append(ChatMessage(role=role, content=content, **kwargs))
        # Keep only the last max_turns * 2 messages (user + assistant pairs)
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2):]

    def get_history_text(self) -> str:
        """Return formatted conversation history as a single string."""
        lines: list[str] = []
        for msg in self.messages:
            prefix = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    def get_last_n_messages(self, n: int) -> list[ChatMessage]:
        """Return the last *n* messages from history."""
        return self.messages[-n:] if n < len(self.messages) else self.messages

# ── Long-Term Memory ──────────────────────────────────────────────────────────

class MemoryRecord(BaseModel):
    """A single fact, preference, or summary stored in long-term memory."""

    memory_id: str = Field(..., description="Unique memory identifier")
    content: str = Field(..., description="Text content of the memory")
    memory_type: str = Field(..., description="Type of memory: fact | preference | summary")
    session_id: str = Field(default="", description="Session from which this memory was extracted")
    score: float | None = Field(default=None, description="Similarity score from search")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Time of memory extraction")


# ── Routing Decision ─────────────────────────────────────────────────────────

class RoutingDecision(BaseModel):
    """
    Captures the router's classification result with full traceability.
    Stored in :class:`AgentState` so the UI can display routing decisions.
    """

    agent: str = Field(..., description="Chosen agent: rag | web | memory | hybrid")
    reasoning: str = Field(
        default="", description="One-sentence explanation from the LLM router"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Router confidence score [0-1]"
    )
    fallback_used: bool = Field(
        default=False, description="True if rule-based fallback was used instead of LLM"
    )
    num_docs_available: int = Field(
        default=0, description="Number of chunks in vector store at routing time"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Agent State (LangGraph) ───────────────────────────────────────────────────

class AgentState(BaseModel):
    """
    Typed state object passed between nodes in the LangGraph workflow.
    All fields are optional so that individual nodes can populate them
    incrementally.
    """

    query: str = Field(..., description="The user's question")
    session_id: str = Field(
        default_factory=lambda: uuid4().hex, description="Session identifier"
    )
    agent_type: AgentType | None = Field(
        default=None, description="Chosen agent for this query"
    )
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    reranked_chunks: list[RetrievedChunk] = Field(default_factory=list)
    web_results: list[dict[str, Any]] = Field(
        default_factory=list, description="Raw Tavily search results"
    )
    context: str = Field(default="", description="Assembled context string for LLM")
    answer: str = Field(default="", description="Final generated answer")
    sources: list[SourceCitation] = Field(default_factory=list)
    conversation_history: list[ChatMessage] = Field(default_factory=list)
    error: str | None = Field(default=None, description="Error message if any node failed")
    latency_ms: dict[str, float] = Field(
        default_factory=dict, description="Per-node latency tracking"
    )
    # ── Routing observability ─────────────────────────────────────
    routing_decision: RoutingDecision | None = Field(
        default=None, description="Full routing classification result"
    )
    routing_trace: list[str] = Field(
        default_factory=list,
        description="Step-by-step log of the routing and execution path",
    )
    # ── Token & Cost observability ────────────────────────────────
    prompt_tokens: int = Field(default=0, description="Sum of prompt tokens used across LLM calls")
    completion_tokens: int = Field(default=0, description="Sum of completion tokens used across LLM calls")
    total_tokens: int = Field(default=0, description="Sum of total tokens used across LLM calls")
    cost_usd: float = Field(default=0.0, description="Estimated cost of LLM calls in USD")
    filter_document_ids: list[str] | None = Field(default=None, description="Optional list of document IDs to restrict retrieval")
    retrieved_memories: list[MemoryRecord] = Field(default_factory=list, description="Memories retrieved for this query")

    model_config = {"arbitrary_types_allowed": True}


# ── API Request / Response Schemas ────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response returned after a successful document upload."""

    document_id: str
    filename: str
    num_chunks: int
    num_pages: int | None = None
    status: DocumentStatus
    message: str


class ChatRequest(BaseModel):
    """Payload for the POST /chat endpoint."""

    query: str = Field(..., min_length=1, max_length=4096, description="User's question")
    session_id: str | None = Field(
        default=None,
        description="Session ID for conversation continuity; generated if omitted",
    )
    use_web_search: bool = Field(
        default=True,
        description="Allow the router to trigger web search when documents are insufficient",
    )
    filter_document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document IDs to restrict search",
    )

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, v: str) -> str:
        """Remove leading/trailing whitespace from the query; reject blank queries."""
        stripped = str(v).strip()
        if not stripped:
            raise ValueError("query must not be blank or whitespace-only")
        return stripped


class ChatResponse(BaseModel):
    """Response returned by the POST /chat endpoint."""

    answer: str
    sources: list[SourceCitation]
    agent_used: AgentType
    session_id: str
    latency_ms: dict[str, float] = Field(default_factory=dict)
    # ── Routing observability ─────────────────────────────────────
    routing_decision: RoutingDecision | None = Field(
        default=None, description="Router's classification result with reasoning"
    )
    routing_trace: list[str] = Field(
        default_factory=list,
        description="Step-by-step execution path through the LangGraph workflow",
    )
    # ── Token & Cost observability ────────────────────────────────
    prompt_tokens: int = Field(default=0, description="Sum of prompt tokens used across LLM calls")
    completion_tokens: int = Field(default=0, description="Sum of completion tokens used across LLM calls")
    total_tokens: int = Field(default=0, description="Sum of total tokens used across LLM calls")
    cost_usd: float = Field(default=0.0, description="Estimated cost of LLM calls in USD")
    retrieved_memories: list[MemoryRecord] = Field(default_factory=list, description="Memories retrieved for this query")


class DocumentListResponse(BaseModel):
    """Response returned by GET /documents."""

    documents: list[DocumentRecord]
    total: int


class DeleteDocumentResponse(BaseModel):
    """Response returned by DELETE /documents/{id}."""

    document_id: str
    message: str
    chunks_deleted: int


class HealthResponse(BaseModel):
    """Response returned by GET /health."""

    status: str
    version: str
    vector_store: str
    embedding_model: str
    llm_model: str
    documents_indexed: int


# ── Analytics ─────────────────────────────────────────────────────────────────

class ScoreDistribution(BaseModel):
    """Score statistics for one retrieval stage."""
    min_score: float | None = None
    max_score: float | None = None
    mean_score: float | None = None
    p50_score: float | None = None  # median
    p90_score: float | None = None  # 90th percentile


class RetrievalMetric(BaseModel):
    """Single retrieval event with full pipeline observability."""

    # ── Identity ──────────────────────────────────────────────────
    query: str
    query_length: int = 0
    agent_type: AgentType
    session_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # ── Retrieval counts ──────────────────────────────────────────
    num_vector_results: int = 0      # Raw results from ChromaDB
    num_bm25_results: int = 0        # Raw results from BM25
    num_retrieved: int = 0           # After RRF fusion
    num_reranked: int = 0            # After cross-encoder reranking

    # ── Stage latencies (ms) ──────────────────────────────────────
    vector_search_latency_ms: float = 0.0
    bm25_search_latency_ms: float = 0.0
    rrf_fusion_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0     # Total hybrid retrieval
    reranking_latency_ms: float | None = None
    llm_latency_ms: float | None = None
    total_latency_ms: float = 0.0

    # ── Score distributions ───────────────────────────────────────
    vector_score_distribution: ScoreDistribution = Field(
        default_factory=ScoreDistribution
    )
    bm25_score_distribution: ScoreDistribution = Field(
        default_factory=ScoreDistribution
    )
    rerank_score_distribution: ScoreDistribution = Field(
        default_factory=ScoreDistribution
    )
    rrf_score_distribution: ScoreDistribution = Field(
        default_factory=ScoreDistribution
    )

    # ── Final output ──────────────────────────────────────────────
    sources_used: list[str] = Field(default_factory=list)
    top_reranked_sources: list[str] = Field(default_factory=list)
    # ── Token & Cost observability ────────────────────────────────
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
