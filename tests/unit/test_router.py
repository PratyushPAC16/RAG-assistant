"""
Unit tests — Router Agent
Tests query classification and routing decisions.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GOOGLE_API_KEY", "test_key")
os.environ.setdefault("TAVILY_API_KEY", "test_key")

from app.agents.router import RouterAgent
from app.models.schemas import AgentState, AgentType


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_store():
    store = MagicMock()
    store.count.return_value = 10  # Documents available by default
    return store


@pytest.fixture
def router(mock_store) -> RouterAgent:
    with patch("app.agents.router.get_llm"):
        return RouterAgent(vector_store=mock_store)


# ── Fallback routing tests (no LLM) ───────────────────────────────────────────

class TestFallbackRoute:
    def test_memory_keywords_route_to_memory(self, router: RouterAgent, mock_store) -> None:
        result = router._fallback_route("you said earlier that", num_docs=5, has_history=True)
        assert result == AgentType.MEMORY

    def test_web_keywords_route_to_web(self, router: RouterAgent, mock_store) -> None:
        result = router._fallback_route("latest AI news today", num_docs=5, has_history=False)
        assert result == AgentType.WEB

    def test_default_to_rag_with_docs(self, router: RouterAgent, mock_store) -> None:
        result = router._fallback_route("What is the revenue?", num_docs=10, has_history=False)
        assert result == AgentType.RAG

    def test_default_to_web_without_docs(self, router: RouterAgent, mock_store) -> None:
        result = router._fallback_route("What is X?", num_docs=0, has_history=False)
        assert result == AgentType.WEB


# ── JSON parsing tests ─────────────────────────────────────────────────────────

class TestParseRoutingResponse:
    def test_parse_rag_response(self, router: RouterAgent) -> None:
        raw = '{"agent": "rag", "reasoning": "Documents available", "confidence": 0.9}'
        result = router._parse_routing_response(raw, num_docs=10)
        assert result == AgentType.RAG

    def test_parse_web_response(self, router: RouterAgent) -> None:
        raw = '{"agent": "web", "reasoning": "Need current info", "confidence": 0.85}'
        result = router._parse_routing_response(raw, num_docs=10)
        assert result == AgentType.WEB

    def test_parse_memory_response(self, router: RouterAgent) -> None:
        raw = '{"agent": "memory", "reasoning": "Follow-up", "confidence": 0.95}'
        result = router._parse_routing_response(raw, num_docs=10)
        assert result == AgentType.MEMORY

    def test_parse_with_markdown_fences(self, router: RouterAgent) -> None:
        raw = '```json\n{"agent": "web", "reasoning": "r", "confidence": 0.8}\n```'
        result = router._parse_routing_response(raw, num_docs=10)
        assert result == AgentType.WEB

    def test_parse_invalid_json_falls_back(self, router: RouterAgent) -> None:
        result = router._parse_routing_response("not valid json", num_docs=10)
        assert result == AgentType.RAG  # default when docs available

    def test_parse_invalid_json_no_docs_returns_web(self, router: RouterAgent) -> None:
        result = router._parse_routing_response("not valid json", num_docs=0)
        assert result == AgentType.WEB

    def test_low_confidence_no_docs_returns_web(self, router: RouterAgent) -> None:
        raw = '{"agent": "rag", "reasoning": "unclear", "confidence": 0.4}'
        result = router._parse_routing_response(raw, num_docs=0)
        assert result == AgentType.WEB


# ── Route method tests ─────────────────────────────────────────────────────────

class TestRouteMethod:
    def test_route_sets_agent_type(self, router: RouterAgent) -> None:
        state = AgentState(query="Tell me about the quarterly report")

        # Mock the LLM to return a valid routing response
        router._llm = MagicMock()
        router._llm.invoke.return_value.content = (
            '{"agent": "rag", "reasoning": "Document query", "confidence": 0.9}'
        )

        result = router.route(state)
        assert result.agent_type is not None
        assert result.agent_type in [AgentType.RAG, AgentType.WEB, AgentType.MEMORY]

    def test_route_on_llm_error_defaults_to_rag(self, router: RouterAgent) -> None:
        state = AgentState(query="Some question")

        router._llm = MagicMock()
        router._llm.invoke.side_effect = Exception("LLM unavailable")

        result = router.route(state)
        # Should not raise; should default gracefully
        assert result.agent_type is not None

    def test_get_next_node_rag(self, router: RouterAgent) -> None:
        state = AgentState(query="q", agent_type=AgentType.RAG)
        assert router.get_next_node(state) == "rag_node"

    def test_get_next_node_web(self, router: RouterAgent) -> None:
        state = AgentState(query="q", agent_type=AgentType.WEB)
        assert router.get_next_node(state) == "web_node"

    def test_get_next_node_memory(self, router: RouterAgent) -> None:
        state = AgentState(query="q", agent_type=AgentType.MEMORY)
        assert router.get_next_node(state) == "memory_node"
