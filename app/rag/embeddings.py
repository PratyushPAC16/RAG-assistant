"""
Enterprise Agentic RAG Assistant
Embeddings module — wraps Google Gemini embeddings with batch support,
retry logic, and consistent error handling.
"""

from __future__ import annotations

import asyncio
import time
from typing import Sequence

from google.api_core.exceptions import GoogleAPIError
from langchain_core.embeddings import Embeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


# ── Retry policy ──────────────────────────────────────────────────────────────

_RETRY_POLICY = dict(
    retry=retry_if_exception_type((GoogleAPIError, ConnectionError, TimeoutError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)


# ── Embedding client ──────────────────────────────────────────────────────────

class EmbeddingService:
    """
    Thin wrapper around :class:`GoogleGenerativeAIEmbeddings` that adds:

    * Automatic batching to stay within API rate limits.
    * Exponential-backoff retry on transient Google API errors.
    * Structured latency logging for every embedding call.

    Attributes:
        model_name: Name of the Gemini embedding model.
        batch_size: Maximum texts per API call.
    """

    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        from app.utils.llm_factory import get_langchain_embeddings
        self._client = get_langchain_embeddings()

        # Set batch size based on settings or defaults
        self.batch_size = batch_size or getattr(settings, "embedding_batch_size", 16)

        # Retrieve model name dynamically from client or settings
        if settings.embedding_provider.lower() == "gemini":
            self.model_name = model_name or settings.embedding_model
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            self._query_client = GoogleGenerativeAIEmbeddings(
                model=self.model_name,
                google_api_key=settings.google_api_key,
                task_type="retrieval_query",
            )
        else:
            self.model_name = (
                model_name or 
                (settings.local_embedding_model if settings.embedding_provider.lower() == "local" 
                 else settings.ollama_embedding_model)
            )
            self._query_client = self._client

        logger.info(
            "EmbeddingService initialised",
            extra={
                "provider": settings.embedding_provider,
                "model": self.model_name,
                "batch_size": self.batch_size,
            },
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate document embeddings for a list of texts.
        Automatically batches calls and retries on transient errors.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (one per input text), same order.

        Raises:
            GoogleAPIError: If all retry attempts are exhausted.
            ValueError: If *texts* is empty.
        """
        if not texts:
            raise ValueError("Cannot embed an empty list of texts.")

        with log_latency(
            logger,
            "embed_documents",
            num_texts=len(texts),
            model=self.model_name,
        ):
            all_embeddings: list[list[float]] = []
            for batch_start in range(0, len(texts), self.batch_size):
                batch = texts[batch_start : batch_start + self.batch_size]
                embeddings = self._embed_batch_with_retry(batch, is_query=False)
                all_embeddings.extend(embeddings)

        logger.debug(
            "Documents embedded",
            extra={"num_texts": len(texts), "embedding_dim": len(all_embeddings[0])},
        )
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """
        Generate an embedding for a single query string.

        Args:
            text: The search query to embed.

        Returns:
            A single embedding vector.

        Raises:
            GoogleAPIError: If all retry attempts are exhausted.
        """
        with log_latency(logger, "embed_query", model=self.model_name):
            result = self._embed_batch_with_retry([text], is_query=True)

        return result[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Async wrapper around :meth:`embed_documents`.
        Runs the synchronous call in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_documents, texts)

    async def aembed_query(self, text: str) -> list[float]:
        """
        Async wrapper around :meth:`embed_query`.
        Runs the synchronous call in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_query, text)

    def get_langchain_embeddings(self) -> Embeddings:
        """
        Return the underlying LangChain embeddings client for direct integration
        with LangChain pipelines (e.g., Chroma vectorstore constructor).
        """
        return self._client

    # ── Private helpers ────────────────────────────────────────────────────────

    @retry(**_RETRY_POLICY)
    def _embed_batch_with_retry(
        self, texts: list[str], *, is_query: bool
    ) -> list[list[float]]:
        """
        Embed a single batch with automatic retries on transient failures.

        Args:
            texts:    Texts to embed (must fit within API limits).
            is_query: True → use query task-type client; False → document client.

        Returns:
            List of embedding vectors for the batch.
        """
        client = self._query_client if is_query else self._client
        try:
            return client.embed_documents(texts)
        except GoogleAPIError as exc:
            logger.warning(
                "Gemini API error during embedding, will retry",
                extra={"error": str(exc), "batch_size": len(texts)},
            )
            raise


# ── Module-level singleton ─────────────────────────────────────────────────────

_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """
    Return the singleton :class:`EmbeddingService` instance.
    Created on first call; subsequent calls reuse the same instance.
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
