"""
Query API — semantic search with grounded answer generation.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
import dataclasses
from app.core.retrieval.retriever import retrieve
from app.core.generation.answer_generator import generate_answer
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic query over the knowledge base.
    Returns a grounded answer with citations traceable to source chunks.
    """
    chunks = await retrieve(
        query=request.query,
        db=db,
        doc_type_filter=request.doc_type_filter,
        department_filter=request.department_filter,
        top_k=request.top_k,
    )

    # Get related doc IDs from graph traversal (docs sharing entities with top chunks)
    related_doc_ids = list({c.doc_id for c in chunks})

    # Convert dataclass objects to dicts for the generation layer
    chunk_dicts = [dataclasses.asdict(c) for c in chunks]

    answer = await generate_answer(
        query=request.query,
        chunks=chunk_dicts,
    )
    answer["query"] = request.query
    return answer
