"""
Enterprise Agentic RAG Assistant
LLM + Embedding provider factory.

Supports three LLM providers:
  - groq   : Free Groq Cloud API (Llama 3, Mixtral) — recommended
  - gemini  : Google Gemini API (requires paid quota)
  - ollama  : Locally-running Ollama models (completely offline)

And two embedding providers:
  - local  : sentence-transformers running on-device — completely free
  - gemini : Google Gemini embedding API
  - ollama : Ollama embedding models (completely offline)

Configure via environment variables in .env:
  LLM_PROVIDER=groq
  EMBEDDING_PROVIDER=local
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── LLM factory ───────────────────────────────────────────────────────────────

def get_provider_llm(
    provider: str,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> BaseChatModel:
    """
    Build and return a chat LLM for a *specific* provider name, bypassing the
    ``LLM_PROVIDER`` setting.  Used by the benchmark runner to call all
    providers in parallel regardless of the active configuration.

    Args:
        provider:          One of ``groq``, ``gemini``, ``ollama``.
        temperature:       Override temperature (defaults to settings.gemini_temperature).
        max_output_tokens: Override max output tokens.

    Raises:
        ValueError: If the provider name is unsupported.
    """
    settings = get_settings()
    temp = temperature if temperature is not None else settings.gemini_temperature
    max_tok = max_output_tokens or settings.gemini_max_output_tokens
    p = provider.lower()
    if p == "groq":
        return _build_groq_llm(settings, temp, max_tok)
    elif p == "gemini":
        return _build_gemini_llm(settings, temp, max_tok)
    elif p == "ollama":
        return _build_ollama_llm(settings, temp, max_tok)
    else:
        raise ValueError(
            f"Unsupported provider '{provider}'. Choose from: groq, gemini, ollama"
        )


def get_llm(
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> BaseChatModel:
    """
    Build and return a chat LLM configured by the ``LLM_PROVIDER`` setting.

    Args:
        temperature:       Override the default temperature from settings.
        max_output_tokens: Override the default max output tokens.

    Returns:
        A LangChain :class:`BaseChatModel` instance.

    Raises:
        ValueError: If the configured provider is not supported.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()
    temp = temperature if temperature is not None else settings.gemini_temperature
    max_tok = max_output_tokens or settings.gemini_max_output_tokens

    if provider == "groq":
        return _build_groq_llm(settings, temp, max_tok)
    elif provider == "gemini":
        return _build_gemini_llm(settings, temp, max_tok)
    elif provider == "ollama":
        return _build_ollama_llm(settings, temp, max_tok)
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. "
            "Choose from: groq, gemini, ollama"
        )


def _build_groq_llm(settings: Any, temperature: float, max_tokens: int) -> BaseChatModel:
    """Build a Groq ChatModel (free tier: 14,400 req/day)."""
    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise ImportError(
            "langchain-groq is required for Groq provider. "
            "Install with: pip install langchain-groq"
        ) from exc

    if not settings.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Get a free key at https://console.groq.com/keys"
        )

    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    logger.info(
        "LLM initialised",
        extra={"provider": "groq", "model": settings.groq_model},
    )
    return llm


def _build_gemini_llm(settings: Any, temperature: float, max_tokens: int) -> BaseChatModel:
    """Build a Google Gemini ChatModel."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise ImportError(
            "langchain-google-genai is required for Gemini provider. "
            "Install with: pip install langchain-google-genai"
        ) from exc

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    logger.info(
        "LLM initialised",
        extra={"provider": "gemini", "model": settings.gemini_model},
    )
    return llm


def _build_ollama_llm(settings: Any, temperature: float, max_tokens: int) -> BaseChatModel:
    """Build an Ollama local ChatModel."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise ImportError(
            "langchain-ollama is required for Ollama provider. "
            "Install with: pip install langchain-ollama"
        ) from exc

    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        num_predict=max_tokens,
    )
    logger.info(
        "LLM initialised",
        extra={"provider": "ollama", "model": settings.ollama_model},
    )
    return llm


# ── Embedding factory ─────────────────────────────────────────────────────────

def get_langchain_embeddings() -> Embeddings:
    """
    Build and return a LangChain Embeddings instance configured by
    the ``EMBEDDING_PROVIDER`` setting.

    Returns:
        A LangChain :class:`Embeddings` instance.

    Raises:
        ValueError: If the configured provider is not supported.
    """
    settings = get_settings()
    provider = settings.embedding_provider.lower()

    if provider == "local":
        return _build_local_embeddings(settings)
    elif provider == "gemini":
        return _build_gemini_embeddings(settings)
    elif provider == "ollama":
        return _build_ollama_embeddings(settings)
    else:
        raise ValueError(
            f"Unsupported EMBEDDING_PROVIDER '{provider}'. "
            "Choose from: local, gemini, ollama"
        )


def _build_local_embeddings(settings: Any) -> Embeddings:
    """
    Build local sentence-transformers embeddings.
    Runs entirely on-device — no API key, no internet needed after first download.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        # Fallback to community package
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "langchain-huggingface is required for local embeddings. "
                "Install with: pip install langchain-huggingface sentence-transformers"
            ) from exc

    model_name = settings.local_embedding_model
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info(
        "Embeddings initialised",
        extra={"provider": "local", "model": model_name},
    )
    return embeddings


def _build_gemini_embeddings(settings: Any) -> Embeddings:
    """Build Google Gemini embedding model."""
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
    except ImportError as exc:
        raise ImportError(
            "langchain-google-genai is required for Gemini embeddings."
        ) from exc

    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
        task_type="retrieval_document",
    )
    logger.info(
        "Embeddings initialised",
        extra={"provider": "gemini", "model": settings.embedding_model},
    )
    return embeddings


def _build_ollama_embeddings(settings: Any) -> Embeddings:
    """Build Ollama local embedding model."""
    try:
        from langchain_ollama import OllamaEmbeddings
    except ImportError as exc:
        raise ImportError(
            "langchain-ollama is required for Ollama embeddings. "
            "Install with: pip install langchain-ollama"
        ) from exc

    embeddings = OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )
    logger.info(
        "Embeddings initialised",
        extra={"provider": "ollama", "model": settings.ollama_embedding_model},
    )
    return embeddings


def extract_token_usage(response: Any) -> tuple[int, int, int]:
    """
    Extract (prompt_tokens, completion_tokens, total_tokens) from a LangChain response.
    """
    prompt = 0
    completion = 0
    total = 0
    
    # 1. Try usage_metadata (standard in newer LangChain versions)
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        prompt = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        completion = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        total = usage.get("total_tokens") or (prompt + completion)
        if total > 0:
            return prompt, completion, total
            
    # 2. Try response_metadata (provider-specific fallback)
    resp_meta = getattr(response, "response_metadata", {})
    if isinstance(resp_meta, dict):
        token_usage = resp_meta.get("token_usage")
        if isinstance(token_usage, dict):
            prompt = token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
            completion = token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
            total = token_usage.get("total_tokens") or (prompt + completion)
            if total > 0:
                return prompt, completion, total
        
        prompt = resp_meta.get("prompt_tokens") or resp_meta.get("input_tokens") or 0
        completion = resp_meta.get("completion_tokens") or resp_meta.get("output_tokens") or 0
        total = resp_meta.get("total_tokens") or (prompt + completion)
        if total > 0:
            return prompt, completion, total

    return 0, 0, 0


def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate cost in USD based on the currently configured provider and model.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()
    return calculate_provider_cost(provider, prompt_tokens, completion_tokens)


# ── Per-provider pricing tables ────────────────────────────────────────────────
# Rates as of 2025 — update when providers change their pricing.
_PRICING: dict[str, tuple[float, float]] = {
    # provider → (input_rate_per_token, output_rate_per_token)  [USD]
    "gemini": (0.075 / 1_000_000, 0.30 / 1_000_000),   # Gemini 2.0 Flash
    "groq":   (0.05  / 1_000_000, 0.08 / 1_000_000),   # Groq llama-3.1-8b-instant
    "ollama": (0.0,               0.0),                  # Local — free
}


def calculate_provider_cost(
    provider: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """
    Calculate cost in USD for a *specific* provider and token counts.
    Used by the benchmark runner to compute per-provider cost estimates.

    Args:
        provider:          One of ``groq``, ``gemini``, ``ollama``.
        prompt_tokens:     Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.

    Returns:
        Estimated cost in USD (0.0 for Ollama).
    """
    input_rate, output_rate = _PRICING.get(provider.lower(), (0.0, 0.0))
    return (prompt_tokens * input_rate) + (completion_tokens * output_rate)

