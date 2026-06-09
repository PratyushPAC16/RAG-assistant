"""
Enterprise Agentic RAG Assistant
PDF Text Extractor Utility — extracts text from PDF byte streams.
"""

from __future__ import annotations

import io
import pypdf
from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text characters from a PDF file byte stream.
    """
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(pdf_file)
        
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
                
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from PDF ({len(reader.pages)} pages)")
        return full_text
    except Exception as exc:
        logger.error(f"Failed to extract text from PDF bytes: {exc}", exc_info=True)
        return ""
