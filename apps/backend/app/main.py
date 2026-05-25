"""
Autonomous Knowledge Intelligence Platform — FastAPI Backend
Entry point: initializes all services and mounts routes.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
import traceback
from fastapi.responses import JSONResponse
from fastapi import Request
from app.core.retrieval.vector_store import init_vector_store
from app.core.pipeline.embedder import init_embedder
from app.core.pipeline.classifier import init_classifier
from app.core.pipeline.entity_extractor import init_entity_extractor
from app.core.generation.answer_generator import init_answer_generator as init_generator
from app.core.graph.builder import init_graph
from app.api.routes import ingest, documents, query, graph, alerts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


from app.core.gemini_client import init_gemini
from app.core.groq_client import init_groq


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup, clean up on shutdown."""
    settings = get_settings()
    settings.ensure_dirs()

    logger.info("🚀 Initializing Knowledge Platform services...")

    # Database
    await init_db(settings.sqlite_path)
    logger.info("✓ SQLite + FTS5 initialized")

    # Vector store
    init_vector_store(settings.chroma_path)
    logger.info("✓ ChromaDB initialized")

    # Initialize shared Gemini client once (new google-genai SDK)
    init_gemini(settings.gemini_api_key)
    init_groq(settings.groq_api_key)

    # Configure each pipeline module with its model name
    # (client is shared via gemini_client.get_client() and groq_client.get_client())
    init_embedder(settings.gemini_api_key, settings.gemini_embedding_model)
    init_classifier(settings.groq_api_key, settings.groq_model)
    init_entity_extractor(settings.groq_api_key, settings.groq_model)
    init_generator(settings.groq_api_key, settings.groq_model)
    logger.info(f"✓ AI pipeline initialized (Groq text: {settings.groq_model}, Gemini embed: {settings.gemini_embedding_model})")

    # Knowledge graph
    init_graph(settings.graphs_path)
    logger.info("✓ Knowledge graph initialized")

    logger.info("✅ All services ready. Knowledge Platform is live.")
    yield

    # Shutdown
    await close_db()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Autonomous Knowledge Intelligence Platform",
    description="Enterprise-grade document intelligence, semantic retrieval, and knowledge graph generation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
settings = get_settings()
origins = settings.cors_origins_list
allow_all = "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if not allow_all else ["*"],
    allow_credentials=not allow_all,  # Must be false if origins is ['*']
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(ingest.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(graph.router)
app.include_router(alerts.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "traceback": traceback.format_exc()}
    )


@app.get("/api/health")
async def health(db=None):
    from app.core.graph.builder import get_graph_stats
    from app.database import get_db
    from sqlalchemy import text
    import contextlib
    alert_counts = {"critical": 0, "total_unresolved": 0}
    async with contextlib.asynccontextmanager(get_db)() as session:
        try:
            result = await session.execute(text(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN severity='CRITICAL' AND resolved=0 THEN 1 ELSE 0 END) as critical "
                "FROM alerts WHERE resolved=0"
            ))
            row = result.fetchone()
            if row:
                alert_counts = {"critical": row.critical or 0, "total_unresolved": row.total or 0}
        except Exception:
            pass
    return {
        "status": "healthy",
        "version": "2.0.0",
        "graph": get_graph_stats(),
        "alerts": alert_counts,
    }


@app.get("/")
async def root():
    return {"message": "Knowledge Intelligence Platform API", "docs": "/docs"}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
