"""
Enterprise RAG Assistant API
FastAPI entrypoint — registers routers, middlewares, rate-limiters, and lifespan.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import get_orchestrator
from app.rag.retriever import get_retriever
from app.rag.vector_store import get_vector_store
from app.utils.config import get_settings
from app.utils.logger import configure_logging, get_logger, set_request_id

# Configure central settings and logger
settings = get_settings()
configure_logging(level=settings.log_level, fmt=settings.log_format)
logger = get_logger(__name__)


# ── Application lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup: initialise singletons and rebuild in-memory document registry.
    Shutdown: logging.
    """
    logger.info("Starting Enterprise Agentic RAG Assistant API")

    # Warn if API Key auth is disabled
    if not settings.api_key:
        logger.warning(
            "API Authentication is disabled (API_KEY is empty). "
            "Destructive/expensive endpoints will be accessible without authentication. "
            "Set API_KEY in your environment/dotenv to secure them."
        )

    # Re-hydrate metrics state
    import app.api.state as state
    state._retrieval_metrics.clear()
    state._retrieval_metrics.extend(state._load_persisted_metrics())

    # Warm up singletons to avoid first-request latency
    _ = get_vector_store()
    state._rebuild_document_registry()
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


# ── CORS Middleware ────────────────────────────────────────────────────────────

_cors_origins = (
    [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    if settings.allowed_origins != "*"
    else ["*"]
)

# CORS: Disable credentials if wildcard is used to comply with browser specs
_allow_credentials = True
if "*" in _cors_origins:
    logger.warning(
        "CORS: wildcard origin (*) detected — disabling credentials to comply with "
        "browser CORS rules. Set ALLOWED_ORIGINS to explicit origins to use credentials."
    )
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate limiting ──────────────────────────────────────────────────────────────

from app.api.dependencies import limiter, _RATE_LIMITING_ENABLED
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

if _RATE_LIMITING_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Middleware: request-ID injection ───────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request, call_next):
    """Attach a unique request-id to each request for log correlation."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ── Register Routers ───────────────────────────────────────────────────────────

from app.api.routers import (
    analytics,
    benchmarks,
    chat,
    documents,
    memory,
    resume,
    system,
    workflows,
)

app.include_router(system.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(memory.router)
app.include_router(resume.router)
app.include_router(analytics.router)
app.include_router(benchmarks.router)
app.include_router(workflows.router)


# ── Re-exports for test compatibility ──────────────────────────────────────────

from app.api.state import _document_registry, _retrieval_metrics, _benchmark_runs
from app.api.dependencies import _sanitize_filename


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
