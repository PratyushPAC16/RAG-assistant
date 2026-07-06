"""
Unit tests for API key authentication (Fix 2).
Tests the _require_api_key dependency in enabled and disabled modes.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GOOGLE_API_KEY", "test_key")
os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client_with_api_key(api_key_value: str) -> TestClient:
    """
    Import app freshly and patch settings.api_key to the given value.
    We patch at the dependency level to avoid touching the singleton cache.
    """
    from app.api.main import app
    return TestClient(app)


# ── Tests for _require_api_key dependency ─────────────────────────────────────


class TestRequireApiKey:
    """Test the auth dependency on a protected endpoint (DELETE /memories)."""

    def test_auth_disabled_passes_without_header(self):
        """When API_KEY env is empty/unset, all requests pass through."""
        import app.api.main as main_mod
        from app.api.main import app

        original_key = main_mod.settings.api_key
        # Temporarily set api_key to empty (auth disabled)
        main_mod.settings.__dict__["api_key"] = ""
        try:
            with TestClient(app) as client:
                with patch("app.api.main.get_memory_store") as mock_store:
                    mock_store.return_value.clear_all.return_value = None
                    response = client.delete("/memories")
            # No auth required → should hit the actual endpoint (200)
            assert response.status_code == 200
        finally:
            main_mod.settings.__dict__["api_key"] = original_key

    def test_auth_enabled_returns_401_without_header(self):
        """When API_KEY is set, missing X-API-Key header returns 401."""
        import app.api.main as main_mod
        from app.api.main import app

        original_key = main_mod.settings.api_key
        main_mod.settings.__dict__["api_key"] = "supersecret"
        try:
            with TestClient(app) as client:
                response = client.delete("/memories")
            assert response.status_code == 401
            data = response.json()
            assert "API key" in data.get("detail", "")
        finally:
            main_mod.settings.__dict__["api_key"] = original_key

    def test_auth_enabled_returns_401_with_wrong_key(self):
        """Wrong API key value returns 401."""
        import app.api.main as main_mod
        from app.api.main import app

        original_key = main_mod.settings.api_key
        main_mod.settings.__dict__["api_key"] = "supersecret"
        try:
            with TestClient(app) as client:
                response = client.delete(
                    "/memories",
                    headers={"X-API-Key": "wrongkey"},
                )
            assert response.status_code == 401
        finally:
            main_mod.settings.__dict__["api_key"] = original_key

    def test_auth_enabled_returns_200_with_correct_key(self):
        """Correct API key passes the auth check."""
        import app.api.main as main_mod
        from app.api.main import app

        original_key = main_mod.settings.api_key
        main_mod.settings.__dict__["api_key"] = "supersecret"
        try:
            with TestClient(app) as client:
                with patch("app.api.main.get_memory_store") as mock_store:
                    mock_store.return_value.clear_all.return_value = None
                    response = client.delete(
                        "/memories",
                        headers={"X-API-Key": "supersecret"},
                    )
            assert response.status_code == 200
        finally:
            main_mod.settings.__dict__["api_key"] = original_key


class TestProtectedEndpointsCoverage:
    """Quick 401 checks for all 7 protected endpoints when auth is enabled."""

    PROTECTED_ROUTES = [
        ("DELETE", "/memories"),
        ("DELETE", "/memories/some-id"),
        ("DELETE", "/documents/some-id"),
        ("DELETE", "/benchmark/history"),
        ("DELETE", "/chat/session/some-id"),
        ("DELETE", "/workflows/some-id"),
        ("POST", "/reload"),
    ]

    def test_all_protected_routes_return_401_without_key(self):
        import app.api.main as main_mod
        from app.api.main import app

        original_key = main_mod.settings.api_key
        main_mod.settings.__dict__["api_key"] = "testkey"
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                for method, path in self.PROTECTED_ROUTES:
                    if method == "DELETE":
                        resp = client.delete(path)
                    else:
                        resp = client.post(path)
                    assert resp.status_code == 401, (
                        f"Expected 401 for {method} {path}, got {resp.status_code}"
                    )
        finally:
            main_mod.settings.__dict__["api_key"] = original_key

    def test_public_routes_not_blocked_by_auth(self):
        """Read-only and public endpoints should still be accessible."""
        import app.api.main as main_mod
        from app.api.main import app

        original_key = main_mod.settings.api_key
        main_mod.settings.__dict__["api_key"] = "testkey"
        PUBLIC_ROUTES = [
            ("GET", "/documents"),
            ("GET", "/memories"),
            ("GET", "/health"),
        ]
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                with patch("app.api.main.get_vector_store") as mock_vs:
                    mock_vs.return_value.count.return_value = 0
                    with patch("app.api.main.get_memory_store") as mock_ms:
                        mock_ms.return_value.list_all_memories.return_value = []
                        for method, path in PUBLIC_ROUTES:
                            resp = client.get(path)
                            assert resp.status_code != 401, (
                                f"Public route {method} {path} should not require auth"
                            )
        finally:
            main_mod.settings.__dict__["api_key"] = original_key
