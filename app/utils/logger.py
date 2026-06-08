"""
Enterprise Agentic RAG Assistant
Structured logging with JSON output, request IDs, and latency tracking.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generator

# ── Context variable for request tracing ──────────────────────────────────────
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(request_id: str | None = None) -> str:
    """Set a request-scoped ID for log correlation. Returns the ID used."""
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """Retrieve the current request-scoped ID."""
    return _request_id_var.get()


# ── JSON formatter ────────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects for structured log ingestion."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach request-id when available
        rid = get_request_id()
        if rid:
            log_obj["request_id"] = rid

        # Attach any extra fields passed via `extra=`
        _BUILTIN_RECORD_KEYS = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "id",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _BUILTIN_RECORD_KEYS and key not in log_obj:
                log_obj[key] = value

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    _FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt="%Y-%m-%d %H:%M:%S")


# ── Module-level bootstrap ────────────────────────────────────────────────────

def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """
    Bootstrap the root logger.  Call this once at application startup.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        fmt:   Output format — 'json' for structured logs, 'text' for dev mode.
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter: logging.Formatter = (
        JSONFormatter() if fmt == "json" else TextFormatter()
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Usage::

        logger = get_logger(__name__)
        logger.info("Processing document", extra={"doc_id": "abc123"})
    """
    return logging.getLogger(name)


# ── Latency context manager ───────────────────────────────────────────────────

@contextmanager
def log_latency(
    logger: logging.Logger,
    operation: str,
    level: int = logging.INFO,
    **extra_fields: Any,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager that measures wall-clock time and emits a latency log entry.

    Usage::

        with log_latency(logger, "embed_documents", num_chunks=42) as ctx:
            embeddings = model.encode(texts)
        # After block: logs {operation: "embed_documents", latency_ms: 123.4, ...}
        # ctx["latency_ms"] is also available after the block.

    Args:
        logger:       Logger instance to emit on.
        operation:    Human-readable name of the measured operation.
        level:        Logging level (default INFO).
        **extra_fields: Additional key-value pairs to include in the log record.

    Yields:
        A mutable dict that will contain ``latency_ms`` after the block exits.
    """
    ctx: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield ctx
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1_000
        ctx["latency_ms"] = round(elapsed_ms, 2)
        logger.log(
            level,
            f"{operation} completed in {elapsed_ms:.1f}ms",
            extra={"operation": operation, "latency_ms": elapsed_ms, **extra_fields},
        )
