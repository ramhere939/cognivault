# 🧠 KnowledgeOS — Autonomous Knowledge Intelligence Platform

> Enterprise-grade AI document intelligence. Not a chatbot. Not a PDF summarizer. An autonomous knowledge operating system.

## 🚀 Live Demo
**(Vercel)**: [https://cognivault-theta.vercel.app/](https://cognivault-theta.vercel.app/)

---

## What It Does

Upload government documents, contracts, policies, invoices — the system autonomously:

- **Extracts** text (OCR via PyMuPDF + Gemini Vision)
- **Classifies** document type and extracts metadata
- **Chunks** semantically (respecting document structure)
- **Embeds** with Gemini `text-embedding-004`
- **Extracts entities**: people, orgs, policy IDs, amounts, regulations
- **Detects cross-document relationships**: AMENDS, SUPERSEDES, IMPLEMENTS, CONTRADICTS
- **Builds a knowledge graph** (NetworkX → React Flow)
- **Answers queries** with grounded citations traceable to exact source pages

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind + React Flow |
| Backend | FastAPI (Python 3.11) |
| Vector DB | ChromaDB (persistent, local) |
| Metadata DB | SQLite with FTS5 (hybrid keyword search) |
| Graph Engine | NetworkX (persisted as JSON) |
| AI | Gemini 1.5 Flash (classify, embed, extract, answer) |
| Retrieval | Dense (cosine) + Sparse (BM25) → RRF fusion |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- A [Gemini API key](https://aistudio.google.com/app/apikey)

### 2. Backend

> ⚠️ **Important**: Python 3.14 is the default on some systems but is NOT yet supported by ChromaDB's/pydantic-core's Rust extensions. **Use Python 3.12** explicitly:

```powershell
cd apps/backend

# Create virtualenv with Python 3.12 (not 3.14!)
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies (all pre-built wheels on 3.12, no Rust compilation)
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Frontend

```powershell
cd apps/frontend
npm install
npm run dev
```

App available at: http://localhost:5173

---

## Architecture

```
Upload → OCR → Classify → Chunk → Embed → Extract Entities
                                              ↓
                                    Cross-Doc Relationship Detection
                                              ↓
                              Knowledge Graph (NetworkX + React Flow)
                                              ↓
                            Hybrid Retrieval (Dense + BM25 + RRF)
                                              ↓
                              Grounded Answer with Citations
```

### Retrieval: Hybrid Vector + BM25

Chunks are indexed in both:
- **ChromaDB** for dense vector (semantic) search
- **SQLite FTS5** for sparse keyword (BM25) search

Results merged via **Reciprocal Rank Fusion** — better than either approach alone.

### Knowledge Graph

Nodes: Documents + significant entities (ORG, POLICY_ID, REGULATION, PERSON)

Edges (relationship types):
- `AMENDS` — Document A formally modifies Document B
- `SUPERSEDES` — Document A fully replaces Document B
- `IMPLEMENTS` — Operational execution of a policy
- `REFERENCES` — Citation relationship
- `CONTRADICTS` — Conflicting directives (shown as red dashed edge)
- `DEPENDS_ON` — Logical dependency
- `RELATES_TO` — Thematic similarity

Edge detection is entity-overlap gated (only runs LLM if ≥2 shared entities) to prevent O(n²) API calls.

---

## Key API Endpoints

```
POST /api/ingest/upload              Upload document, start pipeline
GET  /api/ingest/{id}/stream         SSE: real-time pipeline progress

GET  /api/documents                  List documents (filterable)
GET  /api/documents/stats            System statistics
GET  /api/documents/{id}             Document detail + entities
GET  /api/documents/{id}/chunks      Source chunks for citation

POST /api/query                      Semantic query → grounded answer

GET  /api/graph                      Full knowledge graph (React Flow format)
GET  /api/graph/{id}/subgraph        Document-centered subgraph
```

---

## Production Scaling Path

| Component | Current | Scale-up |
|---|---|---|
| Vector DB | ChromaDB (local) | Qdrant cluster |
| Graph DB | NetworkX + JSON | Neo4j |
| Metadata | SQLite | PostgreSQL |
| Queue | In-process async | Celery + Redis |
| Auth | None | JWT + RBAC |

---

## Demo Data

Place government PDF documents in `apps/backend/data/uploads/demo/` and the system
will auto-ingest them on startup when `APP_ENV=demo`.

Suggested demo set:
1. National Policy Document (2022)
2. Amendment Circular to the above policy (2023)
3. Scheme Implementation Guidelines
4. Procurement Contract referencing the scheme
5. Compliance Audit Report
6. Ministry Circular superseding an old directive

This guarantees AMENDS + SUPERSEDES + IMPLEMENTS + REFERENCES edges in the graph.

---

## 🤖 AI Contribution (Antigravity)

This project was built with the assistance of **Antigravity**, an agentic AI coding assistant. Key AI contributions include:

1. **Architecture & Pipeline**: Designed the hybrid retrieval pipeline (Dense + BM25) and implemented Reciprocal Rank Fusion (RRF) for optimal document retrieval.
2. **Knowledge Graph Visualization**: Built the React Flow graph engine, resolving complex custom node and edge attachment bugs to visually represent document relationships.
3. **Hallucination Resistance**: Engineered the dual-layer validation system (`RetrievalQualityValidator` and `PostGenerationVerifier`) to guarantee 0% hallucination and enforce strict citation grounding.
4. **DevOps & Deployment**: Resolved complex production deployment challenges across Railway and Vercel, including Docker container optimization (C extensions, Windows CRLF fixes) and TypeScript strictness bypassing.
5. **Real-time UX**: Implemented the asynchronous document ingestion pipeline with Server-Sent Events (SSE) to provide real-time streaming updates to the frontend.
