import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Extracted / classified metadata
    doc_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="unknown",
        # ENUM: policy|invoice|contract|circular|meeting_note|scheme|compliance|procurement|unknown
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)   # ISO8601
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(String, default="processing")
    # processing | ocr | classifying | chunking | embedding | extracting | graphing | indexed | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flexible metadata bag (keywords, tags, etc.)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    entities: Mapped[list["Entity"]] = relationship(
        "Entity", back_populates="document", cascade="all, delete-orphan"
    )
