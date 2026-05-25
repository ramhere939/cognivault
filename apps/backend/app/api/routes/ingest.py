"""
Ingest API routes.
POST /api/ingest/upload    → start pipeline, return doc_id
GET  /api/ingest/{id}/stream → SSE pipeline progress
"""
import asyncio
import json
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.pipeline.orchestrator import run_ingestion_pipeline, get_job_status
from app.schemas.ingest import IngestionStartResponse

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "application/octet-stream",  # some browsers send this for PDFs
}
MAX_FILE_SIZE_MB = 50

# Store for streaming: doc_id → asyncio.Queue of ProgressEvents
_sse_queues: dict[str, asyncio.Queue] = {}


@router.post("/upload", response_model=IngestionStartResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document and start the ingestion pipeline.
    Returns doc_id immediately; client connects to /stream for progress.
    """
    # Validate file size
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(400, f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)")

    doc_id = str(uuid.uuid4())

    # Create SSE queue for this job
    queue: asyncio.Queue = asyncio.Queue()
    _sse_queues[doc_id] = queue

    # Run pipeline in background, feeding events to queue
    background_tasks.add_task(
        _run_pipeline_to_queue, file_bytes, file.filename or "document.pdf", doc_id, queue
    )

    return IngestionStartResponse(
        doc_id=doc_id,
        filename=file.filename or "document.pdf",
        stream_url=f"/api/ingest/{doc_id}/stream",
    )


async def _run_pipeline_to_queue(
    file_bytes: bytes,
    filename: str,
    doc_id: str,
    queue: asyncio.Queue,
):
    """Run pipeline and push events to the SSE queue."""
    from app.database import async_session_factory
    async with async_session_factory() as db:
        async for event in run_ingestion_pipeline(file_bytes, filename, doc_id, db):
            await queue.put(event)
    await queue.put(None)  # sentinel: pipeline done


@router.get("/{doc_id}/stream")
async def stream_progress(doc_id: str):
    """
    Server-Sent Events stream for ingestion progress.
    Client connects here after upload and receives stage updates.
    """
    queue = _sse_queues.get(doc_id)
    if queue is None:
        # Check job status for already-completed jobs
        status = get_job_status(doc_id)
        if status.get("status") == "unknown":
            raise HTTPException(404, f"No ingestion job found for doc_id: {doc_id}")

    async def event_generator():
        try:
            while True:
                if queue is None:
                    # Already done — emit final status
                    status = get_job_status(doc_id)
                    data = json.dumps(status)
                    yield f"data: {data}\n\n"
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    yield "data: {\"stage\": \"ping\"}\n\n"
                    continue

                if event is None:
                    # Pipeline complete
                    yield "data: {\"stage\": \"done\"}\n\n"
                    _sse_queues.pop(doc_id, None)
                    break

                data = json.dumps(event.model_dump())
                yield f"data: {data}\n\n"

                if event.stage in ("complete", "error"):
                    _sse_queues.pop(doc_id, None)
                    break

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
