"""
ChromaDB vector store wrapper.
Manages two collections: document_chunks and entity_nodes.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
import logging
import threading

logger = logging.getLogger(__name__)

_client: Optional[chromadb.PersistentClient] = None
_chunks_collection = None
_entities_collection = None
_write_lock = threading.Lock()


def init_vector_store(chroma_path: str):
    """Initialize ChromaDB persistent client and collections."""
    global _client, _chunks_collection, _entities_collection

    _client = chromadb.PersistentClient(
        path=chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    _chunks_collection = _client.get_or_create_collection(
        name="document_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    _entities_collection = _client.get_or_create_collection(
        name="entity_nodes",
        metadata={"hnsw:space": "cosine"},
    )

    logger.info(f"ChromaDB initialized at {chroma_path}. "
                f"Chunks: {_chunks_collection.count()}, "
                f"Entities: {_entities_collection.count()}")


def get_chunks_collection():
    if _chunks_collection is None:
        raise RuntimeError("Vector store not initialized. Call init_vector_store first.")
    return _chunks_collection


def get_entities_collection():
    if _entities_collection is None:
        raise RuntimeError("Vector store not initialized. Call init_vector_store first.")
    return _entities_collection


def upsert_chunks(
    chunk_ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
):
    """Batch upsert chunk embeddings. Thread-safe."""
    col = get_chunks_collection()
    with _write_lock:
        col.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )


def query_chunks(
    query_embedding: list[float],
    n_results: int = 10,
    where: Optional[dict] = None,
) -> dict:
    """Dense vector search on chunks collection."""
    col = get_chunks_collection()
    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=min(n_results, max(col.count(), 1)),
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)


def delete_doc_chunks(doc_id: str):
    """Remove all chunks for a document (on re-index). Thread-safe."""
    col = get_chunks_collection()
    with _write_lock:
        col.delete(where={"doc_id": doc_id})
