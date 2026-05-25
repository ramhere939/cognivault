import uuid
from typing import Optional
from sqlalchemy import String, Integer, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=False, index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_header: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ChromaDB vector ID (same as chunk ID by convention)
    embedding_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
