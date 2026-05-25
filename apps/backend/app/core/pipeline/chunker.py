"""
Semantic chunker — NOT naive sliding window.
Respects document structure: headers, paragraphs, page boundaries.
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional
from app.core.pipeline.ocr import PageContent

logger = logging.getLogger(__name__)

TARGET_CHUNK_CHARS = 1500    # ~375 tokens at ~4 chars/token
MAX_CHUNK_CHARS = 2200
MIN_CHUNK_CHARS = 100


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    page_num: Optional[int]
    char_start: int
    char_end: int
    section_header: Optional[str]
    token_count: int  # rough estimate


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _detect_section_header(text: str) -> Optional[str]:
    """Extract section header if the chunk starts with one."""
    lines = text.strip().split("\n")
    if not lines:
        return None
    first_line = lines[0].strip()
    # Heuristics: short line, possibly numbered, possibly ALL CAPS or Title Case
    if len(first_line) < 120 and (
        re.match(r"^[\d]+[.)]\s+", first_line)          # "1. Section Name"
        or re.match(r"^[A-Z][A-Z\s]{4,}$", first_line)  # "SECTION NAME"
        or re.match(r"^(Section|Article|Clause|Chapter)\s+", first_line, re.I)
    ):
        return first_line
    return None


def semantic_chunk(raw_text: str, pages: list[PageContent]) -> list[TextChunk]:
    """
    Chunk strategy:
    1. Split raw text by page markers ([PAGE N])
    2. Within each page, split by double-newlines (paragraph boundaries)
    3. Merge small paragraphs until TARGET_CHUNK_CHARS
    4. Split oversized blocks at sentence boundaries
    """
    chunks: list[TextChunk] = []
    chunk_index = 0
    char_cursor = 0

    # Split by page markers
    page_pattern = re.compile(r"\[PAGE (\d+)\]\n")
    page_splits = page_pattern.split(raw_text)

    # page_splits = ['', '1', 'page1_text', '2', 'page2_text', ...]
    # Reconstruct page segments
    page_segments: list[tuple[int, str]] = []
    i = 0
    while i < len(page_splits):
        part = page_splits[i]
        if re.match(r"^\d+$", part.strip()):
            page_num = int(part.strip())
            text = page_splits[i + 1] if i + 1 < len(page_splits) else ""
            page_segments.append((page_num, text))
            i += 2
        else:
            i += 1

    if not page_segments:
        # No page markers — treat as single page
        page_segments = [(1, raw_text)]

    for page_num, page_text in page_segments:
        paragraphs = [p.strip() for p in re.split(r"\n\n+", page_text) if p.strip()]
        current_chunk_parts: list[str] = []
        current_len = 0
        current_start = char_cursor

        for para in paragraphs:
            # If adding this paragraph would exceed max, flush current chunk
            if current_len + len(para) > MAX_CHUNK_CHARS and current_len > MIN_CHUNK_CHARS:
                chunk_text = "\n\n".join(current_chunk_parts)
                chunks.append(TextChunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    page_num=page_num,
                    char_start=current_start,
                    char_end=current_start + len(chunk_text),
                    section_header=_detect_section_header(chunk_text),
                    token_count=_estimate_tokens(chunk_text),
                ))
                chunk_index += 1
                char_cursor += len(chunk_text)
                current_start = char_cursor
                current_chunk_parts = []
                current_len = 0

            # If a single paragraph is too large, split by sentences
            if len(para) > MAX_CHUNK_CHARS:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    if current_len + len(sent) > MAX_CHUNK_CHARS and current_len > MIN_CHUNK_CHARS:
                        chunk_text = " ".join(current_chunk_parts)
                        chunks.append(TextChunk(
                            content=chunk_text,
                            chunk_index=chunk_index,
                            page_num=page_num,
                            char_start=current_start,
                            char_end=current_start + len(chunk_text),
                            section_header=_detect_section_header(chunk_text),
                            token_count=_estimate_tokens(chunk_text),
                        ))
                        chunk_index += 1
                        char_cursor += len(chunk_text)
                        current_start = char_cursor
                        current_chunk_parts = []
                        current_len = 0
                    current_chunk_parts.append(sent)
                    current_len += len(sent)
            else:
                current_chunk_parts.append(para)
                current_len += len(para)

            # Flush when we hit target size
            if current_len >= TARGET_CHUNK_CHARS:
                chunk_text = "\n\n".join(current_chunk_parts)
                chunks.append(TextChunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    page_num=page_num,
                    char_start=current_start,
                    char_end=current_start + len(chunk_text),
                    section_header=_detect_section_header(chunk_text),
                    token_count=_estimate_tokens(chunk_text),
                ))
                chunk_index += 1
                char_cursor += len(chunk_text)
                current_start = char_cursor
                current_chunk_parts = []
                current_len = 0

        # Flush remaining
        if current_chunk_parts and current_len > MIN_CHUNK_CHARS:
            chunk_text = "\n\n".join(current_chunk_parts)
            chunks.append(TextChunk(
                content=chunk_text,
                chunk_index=chunk_index,
                page_num=page_num,
                char_start=current_start,
                char_end=current_start + len(chunk_text),
                section_header=_detect_section_header(chunk_text),
                token_count=_estimate_tokens(chunk_text),
            ))
            chunk_index += 1
            char_cursor += len(chunk_text)

    logger.info(f"Produced {len(chunks)} chunks from {len(page_segments)} pages")
    return chunks
