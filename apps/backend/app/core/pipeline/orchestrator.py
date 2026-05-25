"""
Pipeline orchestrator — coordinates the full ingestion pipeline.
Streams progress events via async generator (consumed by SSE endpoint).
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from app.core.pipeline import ocr, chunker, embedder, classifier, entity_extractor
from app.core.retrieval import vector_store
from app.core.graph import builder as graph_builder
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.entity import Entity
from app.models.relationship import Relationship
from app.schemas.ingest import ProgressEvent

logger = logging.getLogger(__name__)

# In-memory job status store (sufficient for hackathon; use Redis at scale)
_job_status: dict[str, dict] = {}


def get_job_status(doc_id: str) -> dict:
    return _job_status.get(doc_id, {"status": "unknown"})


async def _emit(doc_id: str, stage: str, progress: int, message: str = "") -> ProgressEvent:
    _job_status[doc_id] = {"stage": stage, "progress": progress, "message": message}
    return ProgressEvent(stage=stage, progress=progress, message=message, doc_id=doc_id)


async def run_ingestion_pipeline(
    file_bytes: bytes,
    filename: str,
    doc_id: str,
    db: AsyncSession,
) -> AsyncGenerator[ProgressEvent, None]:
    """
    Full ingestion pipeline with progress streaming.
    Each yield is a ProgressEvent sent to the client via SSE.
    """
    try:
        # ── Stage 1: OCR / Text Extraction ──────────────────────────
        yield await _emit(doc_id, "ocr", 5, f"Extracting text from {filename}...")
        await asyncio.sleep(0.05)  # allow event to flush

        extracted = await asyncio.get_event_loop().run_in_executor(
            None, lambda: ocr.extract(file_bytes, filename)
        )

        # Dedup check: skip if same file already indexed
        existing = await db.execute(
            text("SELECT id FROM documents WHERE file_hash = :hash"),
            {"hash": extracted.file_hash}
        )
        if existing.fetchone():
            yield await _emit(doc_id, "complete", 100, "Document already indexed (duplicate detected)")
            return

        yield await _emit(doc_id, "ocr", 20, f"Extracted {extracted.page_count} pages, {len(extracted.raw_text)} chars")

        # ── Stage 2: Classification ──────────────────────────────────
        yield await _emit(doc_id, "classify", 25, "Classifying document type and extracting metadata...")
        classification = await classifier.classify_document(extracted.raw_text)
        yield await _emit(doc_id, "classify", 35,
                          f"Classified as: {classification.get('doc_type')} | {classification.get('title') or filename}")

        # Save document record
        doc = Document(
            id=doc_id,
            filename=filename,
            file_hash=extracted.file_hash,
            file_size=extracted.file_size,
            doc_type=classification.get("doc_type"),
            title=classification.get("title"),
            summary=classification.get("summary"),
            doc_date=classification.get("doc_date"),
            author=classification.get("author"),
            department=classification.get("department"),
            page_count=extracted.page_count,
            status="chunking",
            extra_metadata={"keywords": classification.get("keywords", [])},
        )
        db.add(doc)
        await db.commit()

        # Add to knowledge graph immediately
        graph_builder.add_document_node(doc_id, {
            "title": classification.get("title") or filename,
            "filename": filename,
            "doc_type": classification.get("doc_type"),
            "department": classification.get("department"),
            "doc_date": classification.get("doc_date"),
            "summary": classification.get("summary"),
            "status": "processing",
        })

        # ── Stage 3: Semantic Chunking ───────────────────────────────
        yield await _emit(doc_id, "chunk", 40, "Splitting document into semantic chunks...")
        chunks = await asyncio.get_event_loop().run_in_executor(
            None, lambda: chunker.semantic_chunk(extracted.raw_text, extracted.pages)
        )
        yield await _emit(doc_id, "chunk", 48, f"Created {len(chunks)} semantic chunks")

        # Save chunks to DB
        chunk_records = []
        for ch in chunks:
            chunk_rec = Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                content=ch.content,
                chunk_index=ch.chunk_index,
                page_num=ch.page_num,
                char_start=ch.char_start,
                char_end=ch.char_end,
                section_header=ch.section_header,
                token_count=ch.token_count,
            )
            chunk_rec.embedding_id = chunk_rec.id  # same ID used in ChromaDB
            chunk_records.append(chunk_rec)
            db.add(chunk_rec)
        await db.commit()

        # ── Stage 4: Embedding ───────────────────────────────────────
        yield await _emit(doc_id, "embed", 50, f"Generating embeddings for {len(chunks)} chunks...")

        chunk_texts = [ch.content for ch in chunks]
        chunk_ids_for_embed = [cr.id for cr in chunk_records]
        embeddings = await embedder.batch_embed(chunk_texts)

        # Build ChromaDB metadata
        chroma_metadatas = []
        for cr in chunk_records:
            chroma_metadatas.append({
                "doc_id": doc_id,
                "doc_type": classification.get("doc_type"),
                "department": classification.get("department") or "",
                "page_num": cr.page_num or 0,
                "section_header": cr.section_header or "",
                "chunk_index": cr.chunk_index,
            })

        vector_store.upsert_chunks(
            chunk_ids=chunk_ids_for_embed,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=chroma_metadatas,
        )
        yield await _emit(doc_id, "embed", 65, "Vectors indexed in ChromaDB")

        # Populate FTS5 index
        for cr in chunk_records:
            await db.execute(
                text("INSERT INTO chunks_fts(chunk_id, doc_id, content) VALUES(:cid, :did, :content)"),
                {"cid": cr.id, "did": doc_id, "content": cr.content}
            )
        await db.commit()

        # ── Stage 5: Entity Extraction ───────────────────────────────
        yield await _emit(doc_id, "extract", 68, "Extracting named entities and relationships...")
        entities = await entity_extractor.extract_entities(extracted.raw_text, classification.get("doc_type"))
        yield await _emit(doc_id, "extract", 78, f"Extracted {len(entities)} entities")

        entity_records = []
        for ent in entities:
            entity_rec = Entity(
                doc_id=doc_id,
                name=ent.get("name"),
                normalized=ent.get("normalized"),
                entity_type=ent.get("entity_type"),
                evidence_quote=ent.get("evidence_quote"),
                confidence=ent.get("confidence", 0.0),
            )
            db.add(entity_rec)
            entity_records.append(entity_rec)

            # Add significant entities as graph nodes (high confidence only)
            if ent.get("confidence", 0.0) >= 0.75 and ent.get("entity_type") in ["ORG", "POLICY_ID", "REGULATION", "PERSON"]:
                entity_node_id = f"entity_{ent.get('normalized') or ent.get('name')}".replace(" ", "_")[:50]
                graph_builder.add_entity_node(entity_node_id, {
                    "entity_type": ent.get("entity_type"),
                    "name": ent.get("name"),
                    "normalized": ent.get("normalized"),
                    "doc_id": doc_id,
                    "confidence": ent.get("confidence", 0.0),
                })
                graph_builder.add_document_entity_edge(doc_id, entity_node_id, ent.get("name") or "")

        await db.commit()

        # ── Stage 6: Cross-Document Relationship Detection ───────────
        yield await _emit(doc_id, "graph", 82, "Detecting relationships with existing documents...")

        # Get all other indexed documents (limit to last 20 for performance)
        result = await db.execute(
            text("""
                SELECT id, doc_type, title, summary, doc_date, department
                FROM documents
                WHERE id != :doc_id AND status = 'indexed'
                ORDER BY created_at DESC
                LIMIT 20
            """),
            {"doc_id": doc_id}
        )
        other_docs = [dict(row._mapping) for row in result]

        current_entity_names = {e.get("normalized") or e.get("name") for e in entities}

        rel_count = 0
        for other_doc in other_docs:
            # Get entity names for other doc
            ent_result = await db.execute(
                text("SELECT name, normalized FROM entities WHERE doc_id = :did"),
                {"did": other_doc["id"]}
            )
            other_entities = {row.normalized or row.name for row in ent_result}
            shared = current_entity_names & other_entities

            # Only run expensive LLM call if meaningful overlap
            if len(shared) >= 2:
                rel_data = await entity_extractor.detect_relationship(
                    doc_a={
                        "title": classification.get("title"),
                        "doc_type": classification.get("doc_type"),
                        "doc_date": classification.get("doc_date"),
                        "summary": classification.get("summary"),
                    },
                    doc_b=other_doc,
                    shared_entities=list(shared),
                )

                if rel_data:
                    rel_record = Relationship(
                        source_id=doc_id,
                        source_type="document",
                        target_id=other_doc["id"],
                        target_type="document",
                        relation_label=rel_data["relation_label"],
                        confidence=rel_data["confidence"],
                        evidence_quote=rel_data.get("evidence_quote", ""),
                        explanation=rel_data.get("explanation", ""),
                    )
                    db.add(rel_record)

                    graph_builder.add_relationship_edge(
                        source_id=doc_id,
                        target_id=other_doc["id"],
                        relation_label=rel_data["relation_label"],
                        confidence=rel_data["confidence"],
                        evidence_quote=rel_data.get("evidence_quote", ""),
                        explanation=rel_data.get("explanation", ""),
                    )
                    rel_count += 1

        if rel_count > 0:
            await db.commit()

        yield await _emit(doc_id, "graph", 93, f"Found {rel_count} cross-document relationships")

        # ── Finalize ─────────────────────────────────────────────────
        doc.status = "indexed"
        doc.indexed_at = datetime.now(timezone.utc)
        graph_builder.add_document_node(doc_id, {
            "title": classification.get("title") or filename,
            "filename": filename,
            "doc_type": classification.get("doc_type"),
            "department": classification.get("department"),
            "doc_date": classification.get("doc_date"),
            "summary": classification.get("summary"),
            "status": "indexed",
        })
        await db.commit()

        # ── Stage 7: Intelligence Alerts ─────────────────────────────
        yield await _emit(doc_id, "alerts", 96, "Running intelligence alert engine...")
        
        # Fetch data for alert pipeline
        docs_res = await db.execute(text("SELECT id, title, doc_type, summary FROM documents WHERE status='indexed'"))
        all_docs_records = [dict(r._mapping) for r in docs_res]
        
        ents_res = await db.execute(text("SELECT doc_id, entity_type, name, normalized, evidence_quote FROM entities"))
        ents_by_doc = {}
        for r in ents_res:
            ents_by_doc.setdefault(r.doc_id, []).append(dict(r._mapping))
            
        for d in all_docs_records:
            d["entities"] = ents_by_doc.get(d["id"], [])
            
        doc_meta_map = {d["id"]: d for d in all_docs_records}
        
        new_doc_dict = {
            "id": doc_id,
            "title": classification.get("title") or filename,
            "doc_type": classification.get("doc_type"),
            "summary": classification.get("summary"),
            "entities": [{"entity_type": e.get("entity_type"), "name": e.get("name"), "normalized": e.get("normalized"), "evidence_quote": e.get("evidence_quote")} for e in entities]
        }
        
        from app.core.graph.builder import _graph
        from app.core.alerts.engine import run_alert_pipeline
        
        new_alerts = await run_alert_pipeline(
            db=db,
            graph=_graph,
            new_doc=new_doc_dict,
            new_doc_entities=new_doc_dict["entities"],
            all_docs=all_docs_records,
            doc_metadata=doc_meta_map,
        )

        yield await _emit(doc_id, "complete", 100,
                          f"✓ Indexed: {len(chunks)} chunks, {len(entities)} entities, {rel_count} relationships, {len(new_alerts)} new alerts")

    except Exception as e:
        logger.exception(f"Pipeline failed for doc {doc_id}: {e}")
        try:
            await db.execute(
                text("UPDATE documents SET status='failed', error_message=:err WHERE id=:id"),
                {"err": str(e), "id": doc_id}
            )
            await db.commit()
        except Exception:
            pass
        yield ProgressEvent(
            stage="error", progress=0,
            message=f"Pipeline failed: {str(e)}", doc_id=doc_id, error=str(e)
        )
