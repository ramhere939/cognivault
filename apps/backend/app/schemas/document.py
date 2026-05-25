from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentBase(BaseModel):
    filename: str
    doc_type: str
    title: Optional[str] = None
    summary: Optional[str] = None
    doc_date: Optional[str] = None
    author: Optional[str] = None
    department: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: str
    status: str
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    created_at: datetime
    indexed_at: Optional[datetime] = None
    extra_metadata: Optional[dict] = None

    model_config = {"from_attributes": True}


class EntityResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    normalized: Optional[str] = None
    evidence_quote: Optional[str] = None
    confidence: Optional[float] = None

    model_config = {"from_attributes": True}


class ChunkResponse(BaseModel):
    id: str
    doc_id: str
    content: str
    chunk_index: int
    page_num: Optional[int] = None
    section_header: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    entities: list[EntityResponse] = []
    chunk_count: int = 0
