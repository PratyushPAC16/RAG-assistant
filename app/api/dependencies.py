from __future__ import annotations

from pathlib import Path
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.utils.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Define API key header scheme
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(api_key: str = Security(API_KEY_HEADER)) -> None:
    """FastAPI dependency to enforce X-API-Key header authentication."""
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Please provide a valid X-API-Key header.",
        )


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize the uploaded filename to prevent directory traversal attacks.
    Extracts only the base filename and rejects null bytes or traversal characters.
    """
    if not filename:
        return "upload"

    if "\x00" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid characters (null byte).",
        )

    # Extract the basename
    name = Path(filename).name

    # Reject names that attempt directory traversal explicitly or resolve to dots
    if name in (".", "..") or ".." in name or name.startswith("/") or name.startswith("\\"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal attempt detected.",
        )

    return name


# ── Rate Limiter Setup ────────────────────────────────────────────────────────
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    _RATE_LIMITING_ENABLED = True
except ImportError:
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    limiter = DummyLimiter()
    _RATE_LIMITING_ENABLED = False
