from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.models.schemas import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentStatus,
    FileType,
    UploadResponse,
)
from app.rag.document_processor import DocumentProcessor
from app.rag.retriever import get_retriever
from app.rag.vector_store import get_vector_store
from app.utils.config import get_settings
from app.api.dependencies import _require_api_key, _sanitize_filename
from app.api.state import _document_registry

router = APIRouter(tags=["Documents"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a document",
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a PDF, DOCX, or TXT document.

    The document is saved to disk, processed into chunks, embedded using
    Google Gemini, and stored in ChromaDB for retrieval.

    **Supported formats**: `.pdf`, `.docx`, `.txt`
    """
    raw_filename = file.filename or "unknown"
    # Issue 1: Sanitize the filename to prevent directory traversal
    filename = _sanitize_filename(raw_filename)
    extension = Path(filename).suffix.lower().lstrip(".")

    if extension not in ("pdf", "docx", "txt"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '.{extension}'. Allowed: pdf, docx, txt",
        )

    document_id = uuid.uuid4().hex
    save_path = settings.data_path / f"{document_id}_{filename}"

    # Register document as pending
    record = DocumentRecord(
        document_id=document_id,
        filename=filename,
        file_type=FileType(extension),
        status=DocumentStatus.PROCESSING,
        file_size_bytes=0,
    )
    _document_registry[document_id] = record

    try:
        # ── Save uploaded file ──────────────────────────────────────────────
        content = await file.read()

        # ── File size limit ─────────────────────────────────────────────────
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {settings.max_upload_size_mb} MB.",
            )

        # ── MIME-type validation ──────────────────────────────────────────────
        try:
            import magic
            detected_mime = magic.from_buffer(content[:2048], mime=True)
            _ALLOWED_MIMES = {
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
            }
            if detected_mime not in _ALLOWED_MIMES:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=(
                        f"Detected MIME type '{detected_mime}' is not allowed. "
                        f"Allowed types: PDF, DOCX, TXT."
                    ),
                )
        except ImportError:
            # python-magic not available; fall back to extension-only check
            logger.warning("python-magic not available; skipping MIME-type validation")
            
        async with aiofiles.open(save_path, "wb") as f:
            await f.write(content)
        record.file_size_bytes = len(content)

        logger.info(
            "Document uploaded",
            extra={"file_name": filename, "document_id": document_id, "size": len(content)},
        )

        # ── Process and index ──────────────────────────────────────────────────
        processor = DocumentProcessor()
        documents, chunk_metas = processor.process(
            path=save_path, document_id=document_id
        )

        vector_store = get_vector_store()
        vector_store.add_documents(documents, chunk_metas)

        # Refresh BM25 index after adding new documents
        retriever = get_retriever()
        retriever.refresh_bm25_index()

        # ── Update registry ────────────────────────────────────────────────────
        num_pages = max((m.page or 1) for m in chunk_metas) if chunk_metas else None
        record.status = DocumentStatus.INDEXED
        record.num_chunks = len(documents)
        record.num_pages = num_pages
        record.indexed_at = datetime.now(timezone.utc)

        logger.info(
            "Document indexed",
            extra={
                "file_name": filename,
                "document_id": document_id,
                "num_chunks": len(documents),
            },
        )

        return UploadResponse(
            document_id=document_id,
            filename=filename,
            num_chunks=len(documents),
            num_pages=num_pages,
            status=DocumentStatus.INDEXED,
            message=f"Successfully indexed {len(documents)} chunks from '{filename}'.",
        )

    except Exception as exc:
        record.status = DocumentStatus.FAILED
        record.error_message = str(exc)
        logger.error(
            "Document indexing failed",
            extra={"file_name": filename, "error": str(exc)},
            exc_info=True,
        )
        # Clean up saved file on failure
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document. Check server logs for details.",
        )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
)
async def list_documents() -> DocumentListResponse:
    """
    Return a list of all documents that have been uploaded and indexed.
    """
    docs = list(_document_registry.values())
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document and its chunks",
    dependencies=[Depends(_require_api_key)],
)
async def delete_document(document_id: str) -> DeleteDocumentResponse:
    """
    Remove a document and all its associated vector embeddings from the system.
    """
    if document_id not in _document_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    record = _document_registry[document_id]

    try:
        # Delete from vector store
        vector_store = get_vector_store()
        chunks_deleted = vector_store.delete_by_document_id(document_id)

        # Delete file from disk
        for save_path in settings.data_path.glob(f"{document_id}_*"):
            save_path.unlink()

        # Rebuild BM25 index after deletion (non-fatal if it fails)
        retriever = get_retriever()
        try:
            retriever.refresh_bm25_index()
        except Exception as bm25_exc:
            logger.error(
                "BM25 index refresh failed after document deletion",
                extra={"document_id": document_id, "error": str(bm25_exc)},
                exc_info=True,
            )

        # Remove from registry
        del _document_registry[document_id]

        logger.info(
            "Document deleted",
            extra={"document_id": document_id, "chunks_deleted": chunks_deleted},
        )

        return DeleteDocumentResponse(
            document_id=document_id,
            message=f"Document '{record.filename}' deleted successfully.",
            chunks_deleted=chunks_deleted,
        )

    except Exception as exc:
        logger.error(
            "Document deletion failed",
            extra={"document_id": document_id, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document. Check server logs for details.",
        )


@router.post(
    "/documents/{document_id}/reindex",
    response_model=UploadResponse,
    summary="Reindex an existing document",
)
async def reindex_document(document_id: str) -> UploadResponse:
    """
    Delete and re-index a document using its saved source file on disk.
    This parses the file and re-adds its text chunks into ChromaDB.
    """
    if document_id not in _document_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    record = _document_registry[document_id]
    filename = record.filename
    save_path = settings.data_path / f"{document_id}_{filename}"

    if not save_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source file for '{filename}' is missing on disk.",
        )

    record.status = DocumentStatus.PROCESSING
    try:
        # Delete from vector store first
        vector_store = get_vector_store()
        vector_store.delete_by_document_id(document_id)

        # Reprocess and index
        processor = DocumentProcessor()
        documents, chunk_metas = processor.process(
            path=save_path, document_id=document_id
        )

        vector_store.add_documents(documents, chunk_metas)

        # Refresh BM25 index after reindexing
        retriever = get_retriever()
        retriever.refresh_bm25_index()

        # Update registry record
        num_pages = max((m.page or 1) for m in chunk_metas) if chunk_metas else None
        record.status = DocumentStatus.INDEXED
        record.num_chunks = len(documents)
        record.num_pages = num_pages
        record.indexed_at = datetime.now(timezone.utc)

        logger.info(
            "Document reindexed",
            extra={
                "file_name": filename,
                "document_id": document_id,
                "num_chunks": len(documents),
            },
        )

        return UploadResponse(
            document_id=document_id,
            filename=filename,
            num_chunks=len(documents),
            num_pages=num_pages,
            status=DocumentStatus.INDEXED,
            message=f"Successfully reindexed {len(documents)} chunks from '{filename}'.",
        )

    except Exception as exc:
        record.status = DocumentStatus.FAILED
        record.error_message = str(exc)
        logger.error(
            "Document reindexing failed",
            extra={"file_name": filename, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reprocess document. Check server logs for details.",
        )
