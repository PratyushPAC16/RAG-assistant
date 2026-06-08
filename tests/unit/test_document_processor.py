"""
Unit tests — Document Processor
Tests text extraction, chunking, and metadata generation for all file formats.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.rag.document_processor import (
    DocumentProcessor,
    _chunk_id,
    _detect_file_type,
    _extract_txt,
)
from app.models.schemas import FileType


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def txt_file(tmp_path: Path) -> Path:
    """Create a temporary TXT file with known content."""
    p = tmp_path / "test_doc.txt"
    p.write_text(
        "This is a test document.\n\n"
        "It has multiple paragraphs.\n\n"
        "Each paragraph contains distinct information about enterprise systems.",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def processor() -> DocumentProcessor:
    return DocumentProcessor()


# ── File type detection tests ──────────────────────────────────────────────────

class TestDetectFileType:
    def test_detect_pdf(self, tmp_path: Path) -> None:
        p = tmp_path / "report.pdf"
        p.touch()
        assert _detect_file_type(p) == FileType.PDF

    def test_detect_docx(self, tmp_path: Path) -> None:
        p = tmp_path / "document.docx"
        p.touch()
        assert _detect_file_type(p) == FileType.DOCX

    def test_detect_txt(self, tmp_path: Path) -> None:
        p = tmp_path / "notes.txt"
        p.touch()
        assert _detect_file_type(p) == FileType.TXT

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "image.png"
        p.touch()
        with pytest.raises(ValueError, match="Unsupported file type"):
            _detect_file_type(p)

    def test_case_insensitive_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "DOCUMENT.PDF"
        p.touch()
        assert _detect_file_type(p) == FileType.PDF


# ── TXT extraction tests ───────────────────────────────────────────────────────

class TestExtractTxt:
    def test_returns_single_page(self, txt_file: Path) -> None:
        pages = _extract_txt(txt_file)
        assert len(pages) == 1
        assert pages[0][0] == 1  # Page number is always 1

    def test_content_preserved(self, txt_file: Path) -> None:
        pages = _extract_txt(txt_file)
        assert "enterprise systems" in pages[0][1]

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.txt"
        p.write_text("", encoding="utf-8")
        pages = _extract_txt(p)
        assert len(pages) == 1
        assert pages[0][1] == ""


# ── Chunk ID generation tests ──────────────────────────────────────────────────

class TestChunkId:
    def test_deterministic(self) -> None:
        cid1 = _chunk_id("report.pdf", 1, 0)
        cid2 = _chunk_id("report.pdf", 1, 0)
        assert cid1 == cid2

    def test_unique_for_different_inputs(self) -> None:
        cid1 = _chunk_id("report.pdf", 1, 0)
        cid2 = _chunk_id("report.pdf", 1, 1)
        cid3 = _chunk_id("other.pdf", 1, 0)
        assert cid1 != cid2
        assert cid1 != cid3

    def test_format(self) -> None:
        cid = _chunk_id("doc.pdf", 1, 0)
        assert cid.startswith("chunk_")
        assert len(cid) == len("chunk_") + 12


# ── DocumentProcessor integration tests ───────────────────────────────────────

class TestDocumentProcessor:
    def test_process_txt_returns_chunks(
        self, processor: DocumentProcessor, txt_file: Path
    ) -> None:
        docs, metas = processor.process(txt_file, document_id="doc123")
        assert len(docs) > 0
        assert len(docs) == len(metas)

    def test_chunk_metadata_populated(
        self, processor: DocumentProcessor, txt_file: Path
    ) -> None:
        docs, metas = processor.process(txt_file, document_id="doc123")
        for meta in metas:
            assert meta.source == txt_file.name
            assert meta.document_id == "doc123"
            assert meta.chunk_id.startswith("chunk_")
            assert meta.page is not None

    def test_file_not_found_raises(self, processor: DocumentProcessor) -> None:
        with pytest.raises(FileNotFoundError):
            processor.process("/nonexistent/file.txt", document_id="x")

    def test_iter_chunks_yields_pairs(
        self, processor: DocumentProcessor, txt_file: Path
    ) -> None:
        pairs = list(processor.iter_chunks(txt_file, document_id="doc456"))
        assert len(pairs) > 0
        for doc, meta in pairs:
            assert doc.page_content
            assert meta.chunk_id

    def test_chunk_content_not_empty(
        self, processor: DocumentProcessor, txt_file: Path
    ) -> None:
        docs, _ = processor.process(txt_file, document_id="doc789")
        for doc in docs:
            assert doc.page_content.strip()
