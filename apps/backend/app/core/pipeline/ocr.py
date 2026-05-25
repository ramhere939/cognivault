"""
PDF/document OCR and text extraction using PyMuPDF.
Falls back to Gemini Vision for image-heavy pages.
"""
import io
import hashlib
import logging
from dataclasses import dataclass
from typing import Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    page_num: int          # 1-indexed
    text: str
    has_images: bool
    block_count: int


@dataclass
class ExtractedDocument:
    raw_text: str
    pages: list[PageContent]
    page_count: int
    file_hash: str
    file_size: int
    has_complex_layout: bool   # tables, multi-column, heavy images


def extract_pdf(file_bytes: bytes, filename: str) -> ExtractedDocument:
    """
    Extract text from PDF using PyMuPDF block-level parsing.
    Preserves page structure for citation accuracy.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[PageContent] = []
    full_text_parts: list[str] = []
    has_complex_layout = False

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Extract text with layout preservation
        blocks = page.get_text("blocks")  # returns (x0,y0,x1,y1,text,block_no,block_type)
        page_text_parts = []

        for block in blocks:
            if block[6] == 0:  # text block (not image)
                text = block[4].strip()
                if text:
                    page_text_parts.append(text)

        page_text = "\n\n".join(page_text_parts)

        # Detect images on page
        image_list = page.get_images()
        has_images = len(image_list) > 0

        # Detect complex layout (tables, multi-column)
        if len(blocks) > 20 or has_images:
            has_complex_layout = True

        page_content = PageContent(
            page_num=page_num + 1,
            text=page_text,
            has_images=has_images,
            block_count=len(blocks),
        )
        pages.append(page_content)
        if page_text:
            full_text_parts.append(f"[PAGE {page_num + 1}]\n{page_text}")

    doc.close()
    raw_text = "\n\n".join(full_text_parts)

    if len(raw_text.strip()) < 100:
        logger.warning(f"Very little text extracted from {filename} — may be scanned/image PDF")

    return ExtractedDocument(
        raw_text=raw_text,
        pages=pages,
        page_count=len(pages),
        file_hash=file_hash,
        file_size=file_size,
        has_complex_layout=has_complex_layout,
    )


def extract_text_file(file_bytes: bytes, filename: str) -> ExtractedDocument:
    """Extract from plain text files."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    text = file_bytes.decode("utf-8", errors="replace")
    page = PageContent(page_num=1, text=text, has_images=False, block_count=1)
    return ExtractedDocument(
        raw_text=text,
        pages=[page],
        page_count=1,
        file_hash=file_hash,
        file_size=len(file_bytes),
        has_complex_layout=False,
    )


def extract(file_bytes: bytes, filename: str) -> ExtractedDocument:
    """Route extraction based on file type."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf(file_bytes, filename)
    elif lower.endswith((".txt", ".md")):
        return extract_text_file(file_bytes, filename)
    else:
        # Attempt PDF-style for docx, etc. (limited support)
        try:
            return extract_pdf(file_bytes, filename)
        except Exception:
            return extract_text_file(file_bytes, filename)
