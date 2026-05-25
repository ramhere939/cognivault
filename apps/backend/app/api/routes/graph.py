"""
Graph API — knowledge graph endpoints for React Flow.
"""
from fastapi import APIRouter, Query
from app.core.graph.serializer import serialize_graph, serialize_subgraph
from app.core.graph.builder import get_graph_stats
from app.schemas.graph import GraphResponse

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_full_graph(
    hide_mentions: bool = Query(True, description="Hide MENTIONS edges for cleaner view"),
):
    """Full knowledge graph in React Flow format."""
    return serialize_graph(hide_mentions=hide_mentions)


@router.get("/stats")
async def graph_stats():
    """Graph statistics."""
    return get_graph_stats()


@router.get("/{doc_id}/subgraph", response_model=GraphResponse)
async def get_document_subgraph(
    doc_id: str,
    depth: int = Query(2, ge=1, le=3),
):
    """Subgraph centered on a specific document, showing all connected nodes."""
    return serialize_subgraph(doc_id=doc_id, depth=depth)


@router.get("/{doc_id}/impact", response_model=GraphResponse)
async def get_document_impact_graph(doc_id: str):
    """Impact graph tracing descendants of a document via operational edges."""
    from app.core.graph.serializer import serialize_impact_graph
    return serialize_impact_graph(doc_id)


@router.get("/{doc_id}/dependencies", response_model=GraphResponse)
async def get_document_dependency_graph(doc_id: str):
    """Dependency graph tracing ancestors of a document via operational edges."""
    from app.core.graph.serializer import serialize_dependency_graph
    return serialize_dependency_graph(doc_id)
