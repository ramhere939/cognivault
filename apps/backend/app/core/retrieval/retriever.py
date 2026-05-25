"""
Hybrid retriever: dense vector search + BM25 keyword search.
Merges results with Reciprocal Rank Fusion (RRF).
"""
import logging
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.retrieval.vector_store import query_chunks
from app.core.pipeline.embedder import embed_query

logger = logging.getLogger(__name__)

RRF_K = 60  # RRF constant — standard value


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    content: str
    page_num: Optional[int]
    section_header: Optional[str]
    doc_type: str
    doc_title: Optional[str]
    relevance_score: float
    retrieval_method: str  # "dense" | "sparse" | "hybrid"


def _reciprocal_rank_fusion(
    dense_results: list[tuple[str, float]],   # (chunk_id, score)
    sparse_results: list[tuple[str, float]],
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """
    Merge ranked lists using RRF.
    Score = sum(1/(k + rank)) across all lists.
    """
    scores: dict[str, float] = {}

    for rank, (chunk_id, _) in enumerate(dense_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)

    for rank, (chunk_id, _) in enumerate(sparse_results):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def retrieve(
    query: str,
    db: AsyncSession,
    doc_type_filter: Optional[str] = None,
    department_filter: Optional[str] = None,
    top_k: int = 5,
    over_retrieve: int = 15,
) -> list[RetrievedChunk]:
    """
    Hybrid retrieval pipeline:
    1. Dense vector search via ChromaDB
    2. BM25 keyword search via SQLite FTS5
    3. RRF fusion
    4. Enrich with DB metadata
    """
    # ── 1. Dense retrieval ──────────────────────────────────────────
    query_embedding = await embed_query(query)

    chroma_where = {}
    if doc_type_filter:
        chroma_where["doc_type"] = doc_type_filter
    if department_filter:
        chroma_where["department"] = department_filter

    chroma_results = query_chunks(
        query_embedding=query_embedding,
        n_results=over_retrieve,
        where=chroma_where if chroma_where else None,
    )

    dense_ranked: list[tuple[str, float]] = []
    chroma_ids = chroma_results.get("ids", [[]])[0]
    chroma_distances = chroma_results.get("distances", [[]])[0]
    for chunk_id, distance in zip(chroma_ids, chroma_distances):
        score = 1.0 - distance  # convert cosine distance to similarity
        dense_ranked.append((chunk_id, score))

    # ── 2. Sparse BM25 retrieval via SQLite FTS5 ────────────────────
    fts_query = " OR ".join(f'"{word}"' for word in query.split() if len(word) > 2)
    sparse_ranked: list[tuple[str, float]] = []

    if fts_query:
        try:
            result = await db.execute(
                text("""
                    SELECT chunk_id, bm25(chunks_fts) as score
                    FROM chunks_fts
                    WHERE chunks_fts MATCH :query
                    ORDER BY bm25(chunks_fts)
                    LIMIT :limit
                """),
                {"query": fts_query, "limit": over_retrieve}
            )
            for row in result:
                sparse_ranked.append((row.chunk_id, abs(float(row.score))))
        except Exception as e:
            logger.warning(f"FTS5 search failed (table may be empty): {e}")

    # ── 3. RRF Fusion ───────────────────────────────────────────────
    fused = _reciprocal_rank_fusion(dense_ranked, sparse_ranked)
    top_chunk_ids = [chunk_id for chunk_id, _ in fused[:over_retrieve]]

    if not top_chunk_ids:
        return []

    # ── 4. Enrich with metadata from SQLite ─────────────────────────
    placeholders = ", ".join(f":id{i}" for i in range(len(top_chunk_ids)))
    params = {f"id{i}": cid for i, cid in enumerate(top_chunk_ids)}

    result = await db.execute(
        text(f"""
            SELECT
                c.id as chunk_id,
                c.doc_id,
                c.content,
                c.page_num,
                c.section_header,
                d.doc_type,
                d.title as doc_title
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            WHERE c.id IN ({placeholders})
        """),
        params,
    )

    rows = {row.chunk_id: row for row in result}

    # Build final results preserving RRF order
    retrieved: list[RetrievedChunk] = []
    for chunk_id, rrf_score in fused[:top_k]:
        row = rows.get(chunk_id)
        if row:
            retrieved.append(RetrievedChunk(
                chunk_id=chunk_id,
                doc_id=row.doc_id,
                content=row.content,
                page_num=row.page_num,
                section_header=row.section_header,
                doc_type=row.doc_type,
                doc_title=row.doc_title,
                relevance_score=round(rrf_score, 4),
                retrieval_method="hybrid" if (dense_ranked and sparse_ranked) else
                                 "dense" if dense_ranked else "sparse",
            ))

    logger.info(f"Retrieved {len(retrieved)} chunks for query: '{query[:50]}...'")
    return retrieved
