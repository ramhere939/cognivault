from typing import Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    doc_type_filter: Optional[str] = None     # filter to specific doc type
    department_filter: Optional[str] = None   # filter to department
    top_k: int = 5


class Citation(BaseModel):
    doc_id: str
    doc_title: Optional[str] = None
    doc_type: str
    chunk_id: str
    chunk_content: str
    page_num: Optional[int] = None
    section_header: Optional[str] = None
    relevance_score: float
    highlight_text: Optional[str] = None      # substring to highlight in UI


class QueryResponse(BaseModel):
    query: str
    answer: str
    confidence: float
    citations: list[Citation]
    reasoning_trace: Optional[str] = None
    related_doc_ids: list[str] = []
    gaps: Optional[str] = None
    contradictions: Optional[str] = None
    processing_time_ms: int
