"""
Alert SQLAlchemy model.
Alerts are the primary output of the Intelligence Engine —
proactive, citation-backed, confidence-scored findings.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy import JSON
import enum

from app.database import Base


class AlertType(str, enum.Enum):
    SUPERSESSION        = "SUPERSESSION"         # doc A replaces doc B
    POLICY_CONFLICT     = "POLICY_CONFLICT"       # two docs contradict each other
    MISSING_APPROVAL    = "MISSING_APPROVAL"      # dependency chain broken
    DUPLICATE_INVOICE   = "DUPLICATE_INVOICE"     # same vendor/amount/date pattern
    VENDOR_RISK         = "VENDOR_RISK"           # vendor appears in ≥3 risk contexts
    COMPLIANCE_GAP      = "COMPLIANCE_GAP"        # regulation referenced, no implementing doc
    TIMELINE_ANOMALY    = "TIMELINE_ANOMALY"      # circular dated after the policy it implements
    ORPHANED_REFERENCE  = "ORPHANED_REFERENCE"    # doc references policy ID not in corpus
    OPERATIONAL_BLOCK   = "OPERATIONAL_BLOCK"     # project blocked by unresolved dep
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"   # A ENABLES B ENABLES A


class AlertSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"


class Alert(Base):
    __tablename__ = "alerts"

    id                = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type        = Column(SAEnum(AlertType), nullable=False, index=True)
    severity          = Column(SAEnum(AlertSeverity), nullable=False, index=True)

    title             = Column(String(300), nullable=False)
    explanation       = Column(Text, nullable=False)     # ≤2 sentences, human-readable
    reasoning_trace   = Column(Text, nullable=True)      # how the system concluded this

    # Deduplication key — hash(alert_type + sorted(affected_doc_ids))
    dedup_key         = Column(String(64), unique=True, nullable=False, index=True)

    # Evidence
    affected_doc_ids  = Column(JSON, default=list)       # list of doc UUID strings
    evidence_chunks   = Column(JSON, default=list)       # [{chunk_id, quote, doc_id}]
    graph_edge_id     = Column(String, nullable=True)    # if alert maps to graph edge

    confidence        = Column(Float, nullable=False, default=0.0)
    operational_risk  = Column(Text, nullable=True)      # risk implication narrative

    # Lifecycle
    resolved          = Column(Boolean, default=False, index=True)
    resolved_at       = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))
