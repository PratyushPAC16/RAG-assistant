from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.agents.graph import get_orchestrator
from app.models.schemas import HealthResponse
from app.rag.retriever import get_retriever
from app.rag.vector_store import get_vector_store
from app.utils.config import get_settings
from app.api.dependencies import _require_api_key, limiter
from app.api.state import _rebuild_document_registry

router = APIRouter(tags=["System"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
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


@router.get(
    "/graph",
    summary="Get LangGraph Mermaid representation",
)
async def get_graph() -> dict:
    """
    Return the Mermaid diagram source code of the compiled LangGraph workflow.
    """
    orchestrator = get_orchestrator()
    mermaid_code = orchestrator.get_graph_mermaid()
    return {"mermaid": mermaid_code}


@router.post(
    "/reload",
    summary="Reload configuration and reinitialise all services",
    dependencies=[Depends(_require_api_key)],
)
@limiter.limit("5/minute")
async def reload_config(request: Request) -> dict:
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
        _rebuild_document_registry()
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
            detail="Reload failed. Check server logs for details.",
        )
