from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.models.schemas import (
    BenchmarkRun,
    DocumentRecord,
    DocumentStatus,
    FileType,
    RetrievalMetric,
)
from app.rag.vector_store import get_vector_store
from app.utils.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# ── In-memory document registry ───────────────────────────────────────────────
_document_registry: dict[str, DocumentRecord] = {}

# ── Analytics store ────────────────────────────────────────────────────────────
_retrieval_metrics: list[RetrievalMetric] = []

# ── Local persistence helper paths ──────────────────────────────────────────
METRICS_FILE = settings.data_path / "retrieval_metrics.jsonl"
BENCHMARK_FILE = settings.data_path / "benchmark_runs.jsonl"

# ── Benchmark store ────────────────────────────────────────────────────────────
_benchmark_runs: list[BenchmarkRun] = []


def _load_benchmark_history() -> list[BenchmarkRun]:
    runs: list[BenchmarkRun] = []
    if BENCHMARK_FILE.exists():
        try:
            with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        runs.append(BenchmarkRun.model_validate_json(stripped))
        except Exception as exc:
            logger.error("Failed to load benchmark history", extra={"error": str(exc)}, exc_info=True)
    return runs


def _persist_benchmark_run(run: BenchmarkRun) -> None:
    try:
        BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BENCHMARK_FILE, "a", encoding="utf-8") as f:
            f.write(run.model_dump_json() + "\n")
    except Exception as exc:
        logger.error("Failed to persist benchmark run", extra={"error": str(exc)}, exc_info=True)


def _load_persisted_metrics() -> list[RetrievalMetric]:
    metrics = []
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        metrics.append(RetrievalMetric.model_validate_json(stripped))
            logger.info(
                "Persisted metrics loaded",
                extra={"count": len(metrics), "file": str(METRICS_FILE)},
            )
        except Exception as exc:
            logger.error("Failed to load persisted metrics", extra={"error": str(exc)}, exc_info=True)
    return metrics


def _persist_metric(metric: RetrievalMetric) -> None:
    try:
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(metric.model_dump_json() + "\n")
    except Exception as exc:
        logger.error("Failed to persist metric", extra={"error": str(exc)}, exc_info=True)


def _rebuild_document_registry() -> None:
    """Rebuild in-memory registry of documents from ChromaDB collections."""
    global _document_registry
    try:
        vector_store = get_vector_store()
        metadatas = vector_store.get_all_documents_metadata()
        
        # Group chunks by document_id
        doc_chunks = {}
        for meta in metadatas:
            doc_id = meta.get("document_id")
            if doc_id:
                if doc_id not in doc_chunks:
                    doc_chunks[doc_id] = []
                doc_chunks[doc_id].append(meta)
                
        # Rebuild records
        for doc_id, chunks in doc_chunks.items():
            rep = chunks[0]
            filename = rep.get("document_name") or rep.get("source") or "unknown"
            
            pages = set()
            for c in chunks:
                p = c.get("page")
                if p:
                    pages.add(p)
            num_pages = len(pages) if pages else None
            
            # Infer file type from extension
            ext = Path(filename).suffix.lower().lstrip(".")
            file_type = FileType.TXT
            if ext == "pdf":
                file_type = FileType.PDF
            elif ext == "docx":
                file_type = FileType.DOCX
                
            # Get file size if file exists on disk
            file_size = 0
            save_path = settings.data_path / f"{doc_id}_{filename}"
            if save_path.exists():
                file_size = save_path.stat().st_size
                
            _document_registry[doc_id] = DocumentRecord(
                document_id=doc_id,
                filename=filename,
                file_type=file_type,
                status=DocumentStatus.INDEXED,
                num_chunks=len(chunks),
                num_pages=num_pages,
                file_size_bytes=file_size,
                created_at=datetime.now(timezone.utc),
            )
        logger.info(
            "Document registry rebuilt",
            extra={"count": len(_document_registry)},
        )
    except Exception as exc:
        logger.error(
            "Failed to rebuild document registry",
            extra={"error": str(exc)},
            exc_info=True,
        )
