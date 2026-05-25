from typing import Optional
from pydantic import BaseModel


class IngestionStartResponse(BaseModel):
    doc_id: str
    filename: str
    message: str = "Ingestion started"
    stream_url: str


class ProgressEvent(BaseModel):
    stage: str          # ocr | classify | chunk | embed | extract | graph | complete | error
    progress: int       # 0-100
    message: str = ""
    doc_id: str = ""
    error: Optional[str] = None
