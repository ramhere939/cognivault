"""
Documents API — list, get, chunks, entities.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.entity import Entity
from app.schemas.document import DocumentResponse, DocumentDetailResponse, EntityResponse, ChunkResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    doc_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if status:
        query = query.where(Document.status == status)
    query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats")
async def document_stats(db: AsyncSession = Depends(get_db)):
    """System-wide stats for dashboard."""
    result = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_docs,
                COALESCE(SUM(CASE WHEN status='indexed' THEN 1 ELSE 0 END), 0) as indexed,
                COALESCE(SUM(CASE WHEN status='processing' THEN 1 ELSE 0 END), 0) as processing,
                COALESCE(SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END), 0) as failed
            FROM documents
        """)
    )
    doc_stats = dict(result.fetchone()._mapping)

    chunk_count = await db.execute(text("SELECT COUNT(*) FROM chunks"))
    entity_count = await db.execute(text("SELECT COUNT(*) FROM entities"))
    rel_count = await db.execute(text("SELECT COUNT(*) FROM relationships"))

    return {
        **doc_stats,
        "total_chunks": chunk_count.scalar(),
        "total_entities": entity_count.scalar(),
        "total_relationships": rel_count.scalar(),
    }


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    # Get entities
    ent_result = await db.execute(
        select(Entity).where(Entity.doc_id == doc_id).order_by(Entity.confidence.desc())
    )
    entities = ent_result.scalars().all()

    # Get chunk count
    chunk_count_result = await db.execute(
        select(func.count(Chunk.id)).where(Chunk.doc_id == doc_id)
    )
    chunk_count = chunk_count_result.scalar()

    # Convert to dict, explicitly ignoring un-eager-loaded relationships
    doc_dict = {col.name: getattr(doc, col.name) for col in doc.__table__.columns}
    
    response = DocumentDetailResponse(
        **doc_dict,
        entities=[EntityResponse.model_validate(e) for e in entities],
        chunk_count=chunk_count or 0
    )
    return response


@router.get("/{doc_id}/chunks", response_model=list[ChunkResponse])
async def get_chunks(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chunk)
        .where(Chunk.doc_id == doc_id)
        .order_by(Chunk.chunk_index)
    )
    return result.scalars().all()


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    from app.core.retrieval.vector_store import delete_doc_chunks
    from app.core.graph.builder import remove_document

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, f"Document {doc_id} not found")

    # Remove from vector store
    delete_doc_chunks(doc_id)
    # Remove from graph
    remove_document(doc_id)
    # Remove from SQLite (cascade handles chunks + entities)
    await db.delete(doc)
    await db.commit()

    return {"message": f"Document {doc_id} deleted"}
