"""Alert Pydantic schemas for API serialization."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from app.models.alert import AlertType, AlertSeverity


class EvidenceChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: str | None
    quote: str
    page_num: int | None = None


class AlertResponse(BaseModel):
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    explanation: str
    reasoning_trace: str | None
    affected_doc_ids: list[str]
    evidence_chunks: list[EvidenceChunk]
    confidence: float
    operational_risk: str | None
    resolved: bool
    created_at: datetime
    graph_edge_id: str | None = None

    class Config:
        from_attributes = True


class AlertSummary(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    unresolved: int
    critical_count: int


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int
    page: int
    page_size: int
