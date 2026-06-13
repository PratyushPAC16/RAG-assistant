"""
Enterprise Agentic RAG Assistant
Configuration management using Pydantic Settings.
Loads from environment variables and .env file automatically.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
load_dotenv()

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration object for the entire application.
    All values are overridable via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Provider Selection ─────────────────────────────
    llm_provider: str = Field(
        default="groq",
        description="LLM provider: groq (free) | gemini | ollama",
    )
    embedding_provider: str = Field(
        default="local",
        description="Embedding provider: local (free) | gemini | ollama",
    )

    # ── Google Gemini ────────────────────────────────
    google_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(
        default="gemini-2.0-flash", description="Gemini generation model name"
    )
    gemini_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="LLM temperature"
    )
    gemini_max_output_tokens: int = Field(
        default=8192, description="Maximum output tokens"
    )

    # ── Groq (free tier) ──────────────────────────────
    groq_api_key: str = Field(default="", description="Groq Cloud API key (free tier)")
    groq_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq model name",
    )

    # ── Ollama (local) ─────────────────────────────────
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server base URL",
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama chat model name",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name",
    )

    # ── Tavily Web Search ──────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily search API key")

    # ── Embedding Model ────────────────────────────────
    embedding_model: str = Field(
        default="models/gemini-embedding-001",
        description="Google embedding model (used when EMBEDDING_PROVIDER=gemini)",
    )
    local_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace sentence-transformers model (used when EMBEDDING_PROVIDER=local)",
    )

    # ── Vector Database ───────────────────────────────────────────
    chroma_persist_dir: str = Field(
        default="./chroma_db", description="ChromaDB persistence directory"
    )
    chroma_collection_name: str = Field(
        default="enterprise_rag_docs", description="ChromaDB collection name"
    )

    # ── Retrieval Settings ────────────────────────────────────────
    retrieval_top_k: int = Field(
        default=30, gt=0, description="Number of chunks to retrieve before reranking"
    )
    reranker_top_k: int = Field(
        default=5, gt=0, description="Number of chunks to return after cross-encoder reranking"
    )
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L6-v2",
        description="Cross-encoder reranker model (HuggingFace)",
    )
    rrf_k: int = Field(
        default=60, gt=0, description="RRF constant k (from Cormack et al. 2009)"
    )
    semantic_weight: float = Field(
        default=1.0, ge=0.0, description="Weight applied to semantic RRF scores"
    )
    bm25_weight: float = Field(
        default=1.0, ge=0.0, description="Weight applied to BM25 RRF scores"
    )

    # ── Document Processing ───────────────────────────────────────
    chunk_size: int = Field(
        default=1000, gt=0, description="Text chunk size in characters"
    )
    chunk_overlap: int = Field(
        default=200, ge=0, description="Overlap between consecutive chunks"
    )
    data_dir: str = Field(
        default="./data", description="Directory for uploaded documents"
    )

    # ── API Server ─────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI port")
    api_reload: bool = Field(
        default=False, description="Enable hot-reload for development"
    )
    api_version: str = Field(default="1.0.0", description="API version string")
    # Comma-separated list of allowed CORS origins, or "*" for wildcard.
    # Example: "http://localhost:3000,https://myapp.example.com"
    allowed_origins: str = Field(
        default="*",
        description="Comma-separated CORS allowed origins. Use '*' for wildcard (dev only).",
    )
    # Maximum allowed upload file size in megabytes
    max_upload_size_mb: int = Field(
        default=50,
        gt=0,
        description="Maximum file upload size in megabytes",
    )

    # ── Conversation Memory ───────────────────────────────────────
    max_memory_turns: int = Field(
        default=10, gt=0, description="Maximum conversation turns to retain"
    )

    # ── Logging ──────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json", description="Log output format"
    )

    @field_validator("chroma_persist_dir", "data_dir", mode="before")
    @classmethod
    def resolve_paths(cls, v: str) -> str:
        """Resolve relative paths to absolute paths."""
        return str(Path(v).resolve())

    @property
    def data_path(self) -> Path:
        """Return data directory as a Path object, creating it if absent."""
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_path(self) -> Path:
        """Return ChromaDB directory as a Path object, creating it if absent."""
        p = Path(self.chroma_persist_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.
    Uses LRU cache so the .env file is parsed only once per process.
    """
    return Settings()  # type: ignore[call-arg]
