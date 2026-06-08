"""
Unit tests — LLM and Embeddings Factory
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pytest

from app.utils.config import Settings
from app.utils.llm_factory import get_llm, get_langchain_embeddings
from app.rag.embeddings import EmbeddingService


@pytest.fixture
def mock_settings():
    return Settings(
        llm_provider="gemini",
        embedding_provider="gemini",
        google_api_key="mock_google_key",
        groq_api_key="mock_groq_key",
        tavily_api_key="mock_tavily_key",
    )


def test_get_llm_gemini(mock_settings) -> None:
    with (
        patch("app.utils.llm_factory.get_settings", return_value=mock_settings),
        patch("app.utils.llm_factory._build_gemini_llm") as mock_build,
    ):
        get_llm()
        mock_build.assert_called_once()


def test_get_llm_groq(mock_settings) -> None:
    mock_settings.llm_provider = "groq"
    with (
        patch("app.utils.llm_factory.get_settings", return_value=mock_settings),
        patch("app.utils.llm_factory._build_groq_llm") as mock_build,
    ):
        get_llm()
        mock_build.assert_called_once()


def test_get_llm_ollama(mock_settings) -> None:
    mock_settings.llm_provider = "ollama"
    with (
        patch("app.utils.llm_factory.get_settings", return_value=mock_settings),
        patch("app.utils.llm_factory._build_ollama_llm") as mock_build,
    ):
        get_llm()
        mock_build.assert_called_once()


def test_get_embeddings_gemini(mock_settings) -> None:
    with (
        patch("app.utils.llm_factory.get_settings", return_value=mock_settings),
        patch("app.utils.llm_factory._build_gemini_embeddings") as mock_build,
    ):
        get_langchain_embeddings()
        mock_build.assert_called_once()


def test_get_embeddings_local(mock_settings) -> None:
    mock_settings.embedding_provider = "local"
    with (
        patch("app.utils.llm_factory.get_settings", return_value=mock_settings),
        patch("app.utils.llm_factory._build_local_embeddings") as mock_build,
    ):
        get_langchain_embeddings()
        mock_build.assert_called_once()


def test_get_embeddings_ollama(mock_settings) -> None:
    mock_settings.embedding_provider = "ollama"
    with (
        patch("app.utils.llm_factory.get_settings", return_value=mock_settings),
        patch("app.utils.llm_factory._build_ollama_embeddings") as mock_build,
    ):
        get_langchain_embeddings()
        mock_build.assert_called_once()


def test_embedding_service_initialization(mock_settings) -> None:
    mock_settings.embedding_provider = "ollama"
    mock_embeddings = MagicMock()
    with (
        patch("app.rag.embeddings.settings", mock_settings),
        patch("app.utils.llm_factory.get_langchain_embeddings", return_value=mock_embeddings),
    ):
        svc = EmbeddingService()
        assert svc.model_name == mock_settings.ollama_embedding_model
        assert svc._client == mock_embeddings
        assert svc._query_client == mock_embeddings
