"""
Unit tests for filename sanitization (Fix 1 - path traversal prevention).
Tests _sanitize_filename directly and exercises /upload with traversal filenames.
"""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("GOOGLE_API_KEY", "test_key")
os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")

from app.api.main import _sanitize_filename, app, _document_registry  # noqa: E402


# ── Direct unit tests for _sanitize_filename ─────────────────────────────────


class TestSanitizeFilename:
    def test_strips_path_components_dotdot(self):
        """../../etc/passwd → passwd (directory components stripped)."""
        result = _sanitize_filename("../../etc/passwd")
        assert result == "passwd"

    def test_strips_unix_absolute_path(self):
        """/etc/passwd → passwd."""
        result = _sanitize_filename("/etc/passwd")
        assert result == "passwd"

    def test_normal_filename_unchanged(self):
        """A normal filename passes through unchanged."""
        result = _sanitize_filename("my_resume_2024.pdf")
        assert result == "my_resume_2024.pdf"

    def test_empty_filename_returns_upload(self):
        """An empty filename falls back to 'upload'."""
        result = _sanitize_filename("")
        assert result == "upload"

    def test_null_byte_raises_400(self):
        """A null byte in the filename raises HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            _sanitize_filename("evil\x00.txt")
        assert exc_info.value.status_code == 400
        assert "null byte" in exc_info.value.detail.lower()

    def test_dotdot_alone_raises_400(self):
        """Bare '..' resolves via Path.name to '..' and must be rejected."""
        with pytest.raises(HTTPException) as exc_info:
            _sanitize_filename("..")
        assert exc_info.value.status_code == 400

    def test_traversal_stripped_to_safe_basename(self):
        """../../evil.pdf → evil.pdf — traversal stripped, not blanket rejected."""
        result = _sanitize_filename("../../evil.pdf")
        assert result == "evil.pdf"

    def test_filename_with_spaces_allowed(self):
        """Filenames with spaces are accepted."""
        result = _sanitize_filename("my document 2024.pdf")
        assert result == "my document 2024.pdf"

    def test_resulting_path_stays_within_data_dir(self):
        """Core security property: save_path must stay inside data_path."""
        from app.utils.config import get_settings
        s = get_settings()
        safe_name = _sanitize_filename("../../etc/cron.d/evil")
        doc_id = "abc123"
        save_path = s.data_path / f"{doc_id}_{safe_name}"
        assert str(save_path.resolve()).startswith(str(s.data_path.resolve()))
        assert "/" not in safe_name
        assert "\\" not in safe_name


# ── Integration tests: /upload endpoint ──────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_registry():
    _document_registry.clear()
    yield
    _document_registry.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestUploadPathTraversalRejection:
    def test_upload_unsupported_type_returns_415(self, client: TestClient):
        """Baseline: unsupported extension returns 415 after sanitization."""
        response = client.post(
            "/upload",
            files={"file": ("image.png", b"fake", "image/png")},
        )
        assert response.status_code == 415

    def test_upload_traversal_filename_no_valid_ext_returns_415(self, client: TestClient):
        """
        ../../etc/evil → stripped to 'evil' → no valid extension → 415.
        This confirms traversal filenames are handled safely (either stripped or
        rejected at the extension gate — never written to a dangerous path).
        """
        response = client.post(
            "/upload",
            files={"file": ("../../etc/evil", b"content", "application/octet-stream")},
        )
        # After stripping: filename='evil', extension='' → 415 Unsupported Media Type
        assert response.status_code == 415
