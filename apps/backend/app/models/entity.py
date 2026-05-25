import uuid
from typing import Optional
from sqlalchemy import String, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("chunks.id"), nullable=True)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    # PERSON | ORG | DATE | AMOUNT | POLICY_ID | LOCATION | REGULATION | KEYWORD
    entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    normalized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # canonical form

    # Evidence: the exact text passage that justifies this entity
    evidence_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="entities")
