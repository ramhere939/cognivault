import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, JSON, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    source_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)   # document | entity
    target_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String, nullable=False)

    # Relationship taxonomy — enterprise-grade labels
    # AMENDS | SUPERSEDES | IMPLEMENTS | REFERENCES | CONTRADICTS | DEPENDS_ON | RELATES_TO
    relation_label: Mapped[str] = mapped_column(String, nullable=False, index=True)

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # What chunk/passage proved this relationship
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_chunk_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
