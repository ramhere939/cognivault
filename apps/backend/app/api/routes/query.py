"""
Query API — semantic search with grounded answer generation.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
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

    # Convert Pydantic models to dicts for the generation layer
    chunk_dicts = []
    for c in chunks:
        if hasattr(c, "model_dump"):
            chunk_dicts.append(c.model_dump())
        elif hasattr(c, "dict"):
            chunk_dicts.append(c.dict())
        else:
            chunk_dicts.append(c)

    answer = await generate_answer(
        query=request.query,
        chunks=chunk_dicts,
    )
    return answer
