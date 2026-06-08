"""
pytest configuration and shared fixtures.
"""

from __future__ import annotations

import os

import pytest

# ── Ensure required env vars are set before any imports ───────────────────────
os.environ.setdefault("GOOGLE_API_KEY", "test_google_key_conftest")
os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key_conftest")
os.environ.setdefault("CHROMA_PERSIST_DIR", "/tmp/test_chroma_db")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Session-scoped fixture that sets up the test environment."""
    # Ensure test data directory exists
    os.makedirs("/tmp/test_chroma_db", exist_ok=True)
    yield
    # Cleanup is handled by individual test fixtures
