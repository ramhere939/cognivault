# Autonomous Knowledge Intelligence Platform
## Architecture & Execution Plan — Senior Architect Review

---

## TL;DR — What This Actually Is

You're building a **document intelligence operating system** — not a RAG wrapper.

The core loop is:
```
Ingest → OCR/Parse → Semantic Chunk → Embed → Extract Entities →
Build Graph → Index → Query → Cite → Visualize
```

The differentiator lives in the middle: **entity extraction + relationship graph generation**. 
That's what separates this from "another RAG app" in every judge's mind.

---

## Critical Architecture Decisions (Made Upfront)

### Decision 1: Monorepo, Not Microservices
**Why**: Hackathon timeline. One repo, one deploy, zero coordination overhead.  
**Structure**: `apps/frontend` + `apps/backend` + `packages/shared`  
**Scalable path**: Extract services later when you have load to justify it.

### Decision 2: FastAPI Backend, Not Node.js
**Why**: AI/ML ecosystem lives in Python. You will be calling LangChain, spaCy, sentence-transformers, PyMuPDF — fighting Node.js wrappers here is pain with no upside.  
**Node.js role**: Zero. Eliminate it from consideration.

### Decision 3: ChromaDB (not Pinecone, not Weaviate)
**Why**: Runs locally, zero infra cost, production-grade, Python-native, persistent on disk.  
**Scalable path**: Swap to Weaviate or Qdrant cluster with one adapter change.  
**Reject Pinecone for hackathon**: Free tier is rate-limited and you don't control latency.

### Decision 4: SQLite + JSON for Graph (not Neo4j)
**Why**: Neo4j requires a separate server, auth, Cypher expertise, and adds 2 hours of setup.  
NetworkX (Python) gives you a full graph engine in memory, persisted as JSON/GEXF.  
**Scalable path**: Serialize the same graph into Neo4j or ArangoDB post-hackathon.

### Decision 5: Gemini API (not local models)
**Why**: You need multimodal (OCR on images/PDFs), fast embeddings, and strong entity extraction. Gemini Flash is fast + cheap + multimodal. Use `gemini-1.5-flash` for pipeline, `gemini-1.5-pro` only for graph generation.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TS)                  │
│  Upload UI │ Knowledge Graph (React Flow) │ Query UI     │
│  Document Explorer │ Entity Panel │ Citation Viewer      │
└──────────────────────────┬──────────────────────────────┘
                           │ REST + SSE (streaming)
┌──────────────────────────▼──────────────────────────────┐
│                   FASTAPI BACKEND                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Ingest API  │  │  Query API   │  │   Graph API    │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │            │
│  ┌──────▼──────────────────────────────────▼──────────┐ │
│  │              PIPELINE ORCHESTRATOR                   │ │
│  │  OCR → Parse → Chunk → Embed → Extract → Graph     │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                  │
│  ┌──────────┐  ┌────────▼──────┐  ┌────────────────────┐ │
│  │ ChromaDB │  │  SQLite Meta  │  │  NetworkX Graph    │ │
│  │ (vectors)│  │  (documents,  │  │  (nodes, edges,    │ │
│  │          │  │   chunks,     │  │   relationships)   │ │
│  │          │  │   entities)   │  │  persisted as GEXF │ │
│  └──────────┘  └───────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
               ┌───────────▼───────────┐
               │     Gemini API        │
               │  Flash: embed, OCR    │
               │  Pro: graph, extract  │
               └───────────────────────┘
```

---

## Monorepo Folder Structure

```
knowledge_platform/
├── apps/
│   ├── frontend/                    # React + TS + Vite + Tailwind
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── upload/
│   │   │   │   │   ├── DropZone.tsx
│   │   │   │   │   └── IngestionProgress.tsx
│   │   │   │   ├── graph/
│   │   │   │   │   ├── KnowledgeGraph.tsx    ← React Flow canvas
│   │   │   │   │   ├── NodeCard.tsx
│   │   │   │   │   └── EdgeTooltip.tsx
│   │   │   │   ├── query/
│   │   │   │   │   ├── QueryPanel.tsx
│   │   │   │   │   ├── AnswerCard.tsx
│   │   │   │   │   └── CitationDrawer.tsx
│   │   │   │   ├── explorer/
│   │   │   │   │   ├── DocumentList.tsx
│   │   │   │   │   ├── EntityPanel.tsx
│   │   │   │   │   └── ChronologyView.tsx
│   │   │   │   └── layout/
│   │   │   │       ├── Sidebar.tsx
│   │   │   │       └── AppShell.tsx
│   │   │   ├── pages/
│   │   │   │   ├── IngestPage.tsx
│   │   │   │   ├── GraphPage.tsx
│   │   │   │   ├── QueryPage.tsx
│   │   │   │   └── ExplorerPage.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useSSE.ts          ← streaming ingestion progress
│   │   │   │   ├── useGraph.ts
│   │   │   │   └── useQuery.ts
│   │   │   ├── store/
│   │   │   │   └── useAppStore.ts     ← Zustand (NOT Redux — overkill)
│   │   │   ├── api/
│   │   │   │   └── client.ts          ← typed API client
│   │   │   └── types/
│   │   │       └── index.ts
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   └── backend/                      # FastAPI Python
│       ├── app/
│       │   ├── main.py               ← FastAPI app entry
│       │   ├── config.py             ← env + settings (Pydantic BaseSettings)
│       │   ├── api/
│       │   │   ├── routes/
│       │   │   │   ├── ingest.py     ← /api/ingest endpoints
│       │   │   │   ├── query.py      ← /api/query endpoints
│       │   │   │   ├── graph.py      ← /api/graph endpoints
│       │   │   │   └── documents.py  ← /api/documents endpoints
│       │   │   └── deps.py           ← dependency injection
│       │   ├── core/
│       │   │   ├── pipeline/
│       │   │   │   ├── orchestrator.py      ← pipeline coordinator
│       │   │   │   ├── ocr.py               ← Gemini Vision / PyMuPDF
│       │   │   │   ├── chunker.py           ← semantic chunking
│       │   │   │   ├── embedder.py          ← Gemini embeddings
│       │   │   │   ├── entity_extractor.py  ← NER + relationship extraction
│       │   │   │   └── classifier.py        ← doc type classification
│       │   │   ├── graph/
│       │   │   │   ├── builder.py           ← NetworkX graph construction
│       │   │   │   ├── enricher.py          ← LLM-powered edge labeling
│       │   │   │   └── serializer.py        ← GEXF/JSON export
│       │   │   ├── retrieval/
│       │   │   │   ├── vector_store.py      ← ChromaDB wrapper
│       │   │   │   ├── reranker.py          ← cross-encoder reranking
│       │   │   │   └── retriever.py         ← hybrid retrieval orchestrator
│       │   │   └── generation/
│       │   │       ├── answer_generator.py  ← RAG answer with citations
│       │   │       └── citation_builder.py  ← source-to-chunk tracing
│       │   ├── models/
│       │   │   ├── document.py       ← SQLAlchemy models
│       │   │   ├── chunk.py
│       │   │   ├── entity.py
│       │   │   └── relationship.py
│       │   ├── schemas/
│       │   │   ├── ingest.py         ← Pydantic request/response schemas
│       │   │   ├── query.py
│       │   │   └── graph.py
│       │   └── services/
│       │       ├── document_service.py
│       │       ├── graph_service.py
│       │       └── search_service.py
│       ├── data/
│       │   ├── chroma/               ← ChromaDB persisted storage
│       │   ├── sqlite/               ← SQLite database
│       │   └── graphs/               ← GEXF graph files
│       ├── requirements.txt
│       └── .env
│
├── packages/
│   └── shared/
│       └── types/                    ← shared type contracts (OpenAPI-generated)
│
├── docker-compose.yml               ← one-command full stack
└── README.md
```

---

## Data Models (The Foundation)

### SQLite Schema

```sql
-- Core document record
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,   -- uuid
    filename    TEXT NOT NULL,
    doc_type    TEXT NOT NULL,      -- ENUM: policy|invoice|contract|circular|meeting_note|scheme|compliance|procurement
    title       TEXT,
    summary     TEXT,               -- LLM-generated
    date        TEXT,               -- extracted date (ISO8601)
    author      TEXT,
    department  TEXT,
    status      TEXT DEFAULT 'processing',  -- processing|indexed|failed
    metadata    JSON,               -- flexible KV bag
    file_hash   TEXT UNIQUE,        -- dedup on content hash
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    indexed_at  DATETIME
);

-- Semantic chunks
CREATE TABLE chunks (
    id          TEXT PRIMARY KEY,
    doc_id      TEXT REFERENCES documents(id),
    content     TEXT NOT NULL,
    chunk_index INTEGER,
    page_num    INTEGER,
    char_start  INTEGER,
    char_end    INTEGER,
    embedding_id TEXT,              -- ChromaDB vector ID
    metadata    JSON
);

-- Extracted entities
CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,      -- PERSON|ORG|DATE|AMOUNT|POLICY_ID|LOCATION|REGULATION
    normalized  TEXT,               -- canonical form
    doc_id      TEXT REFERENCES documents(id),
    chunk_id    TEXT REFERENCES chunks(id),
    confidence  REAL,
    metadata    JSON
);

-- Relationships between documents/entities
CREATE TABLE relationships (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,   -- doc_id or entity_id
    source_type     TEXT NOT NULL,   -- document|entity
    target_id       TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    relation_label  TEXT NOT NULL,   -- AMENDS|SUPERSEDES|REFERENCES|IMPLEMENTS|CONTRADICTS|RELATES_TO
    confidence      REAL,
    evidence        TEXT,            -- the chunk text that proved this relationship
    evidence_chunk_id TEXT,
    metadata        JSON,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

> [!IMPORTANT]
> The `relationships` table is the product differentiator. Judges will see this.
> `AMENDS`, `SUPERSEDES`, `CONTRADICTS` are enterprise-grade relationship types that immediately signal domain understanding.

---

## Pipeline Design — The Core Engine

### Ingestion Pipeline (Orchestrated, Async)

```python
# orchestrator.py — conceptual flow
async def ingest_document(file: UploadFile, doc_id: str) -> AsyncGenerator[ProgressEvent, None]:
    
    yield ProgressEvent(stage="ocr", progress=0, message="Extracting text...")
    raw_text, pages = await ocr.extract(file)                    # Stage 1
    
    yield ProgressEvent(stage="classify", progress=15)
    doc_type, metadata = await classifier.classify(raw_text)     # Stage 2: Gemini Flash
    
    yield ProgressEvent(stage="chunk", progress=25)
    chunks = chunker.semantic_chunk(raw_text, pages)             # Stage 3
    
    yield ProgressEvent(stage="embed", progress=40)
    embeddings = await embedder.batch_embed(chunks)              # Stage 4: Gemini embeddings
    await vector_store.upsert(doc_id, chunks, embeddings)
    
    yield ProgressEvent(stage="entities", progress=60)
    entities = await entity_extractor.extract(raw_text, doc_type) # Stage 5: Gemini Pro
    await db.save_entities(entities)
    
    yield ProgressEvent(stage="relationships", progress=80)
    rels = await graph_builder.find_relationships(doc_id, entities) # Stage 6: cross-doc
    await db.save_relationships(rels)
    
    yield ProgressEvent(stage="graph", progress=90)
    await graph_service.rebuild_subgraph(doc_id)                 # Stage 7
    
    yield ProgressEvent(stage="complete", progress=100)
```

**Stream this to the frontend via Server-Sent Events.** Watching the progress bar tick through stages in real-time is a demo moment. Don't skip this.

### Chunking Strategy — Not Naive

**DO NOT** use fixed-size chunking (512 tokens, 100 overlap). That's tutorial-level.

```python
# semantic_chunk strategy:
# 1. Split by semantic boundaries: headers, section breaks, paragraph groups
# 2. Respect page boundaries (for PDF citation accuracy)
# 3. Target: 300-500 tokens per chunk, never break mid-sentence
# 4. Metadata every chunk: page_num, section_header, chunk_index, doc_type
# 5. For tables: extract as structured JSON chunk, not plain text
```

Use `PyMuPDF` (fitz) for PDF parsing — it gives you block-level structure, not just raw text.

### Entity Extraction — Prompt Engineering Matters

```python
ENTITY_EXTRACTION_PROMPT = """
You are a government document intelligence system.

Extract all entities from this {doc_type} document.

Entity types to extract:
- PERSON: Named individuals with roles
- ORGANIZATION: Departments, agencies, companies  
- POLICY_ID: Any policy/circular/scheme identifiers (e.g., "GoI/2023/Policy-142")
- AMOUNT: Financial figures with currency and context
- DATE: All dates with their semantic meaning (effective_date, issued_date, deadline)
- REGULATION: Legal acts, sections, clauses referenced
- LOCATION: Geographic scope
- KEYWORD: Domain-critical technical terms

For each entity, also extract:
- The exact quote from the document that supports it
- A normalized canonical form
- Confidence score (0-1)

Output as structured JSON.
"""
```

### Relationship Detection — The Differentiator

```python
RELATIONSHIP_DETECTION_PROMPT = """
You are analyzing two government documents for semantic relationships.

Document A: {doc_a_summary} (Type: {doc_a_type}, Date: {doc_a_date})
Document B: {doc_b_summary} (Type: {doc_b_type}, Date: {doc_b_date})

Shared entities: {shared_entities}

Determine if a relationship exists. Valid relationship types:
- AMENDS: Document A formally modifies Document B
- SUPERSEDES: Document A replaces Document B entirely  
- IMPLEMENTS: Document A is the operational execution of Document B
- REFERENCES: Document A cites Document B
- CONTRADICTS: Documents contain conflicting directives
- DEPENDS_ON: Document A cannot be understood without Document B
- RELATES_TO: Thematic/topical relationship only

Return: relationship_type, confidence (0-1), evidence_quote, explanation
If no meaningful relationship: return null

Be conservative. A high-confidence AMENDS is worth more than a low-confidence RELATES_TO.
"""
```

**Critical design note**: Don't run this for every document pair (O(n²) explosion). 
Run it only for documents sharing ≥2 entity overlaps OR same department OR similar embeddings (cosine > 0.75).

---

## Vector Retrieval Strategy

### ChromaDB Collection Design

```python
# Two collections — not one
CHUNKS_COLLECTION = "document_chunks"     # semantic search
ENTITIES_COLLECTION = "entity_nodes"      # entity similarity

# Chunk metadata stored alongside vector (critical for citation)
chunk_metadata = {
    "doc_id": str,
    "doc_type": str,          # enables filtered search
    "department": str,        # enables scoped search  
    "date": str,              # enables temporal filtering
    "page_num": int,
    "section_header": str,
    "chunk_index": int,
}
```

### Hybrid Retrieval (Vector + Keyword)

```python
# retriever.py
async def retrieve(query: str, filters: dict = None, top_k: int = 10):
    # 1. Dense retrieval: vector similarity
    dense_results = await vector_store.query(
        query_embedding=embed(query),
        where=filters,   # ChromaDB metadata filtering
        n_results=top_k * 2  # over-retrieve, then rerank
    )
    
    # 2. Sparse retrieval: BM25 keyword matching (SQLite FTS5)
    sparse_results = await fts_search(query, filters, limit=top_k)
    
    # 3. Merge (RRF - Reciprocal Rank Fusion)
    merged = reciprocal_rank_fusion(dense_results, sparse_results)
    
    # 4. Rerank top-N with cross-encoder (optional: use Gemini for this)
    reranked = await reranker.rerank(query, merged[:top_k])
    
    return reranked[:5]  # return top 5 for generation
```

> [!TIP]
> SQLite has built-in FTS5 (full-text search). Enable it. Zero cost, major quality improvement on exact policy numbers, dates, and named entities.

---

## Knowledge Graph Design

### Node Types

```python
NODE_TYPES = {
    "DOCUMENT": {
        "color": "#4F46E5",  # indigo
        "size": "large",
        "properties": ["title", "doc_type", "date", "department", "summary"]
    },
    "ENTITY": {
        "PERSON":       {"color": "#059669"},  # emerald
        "ORGANIZATION": {"color": "#D97706"},  # amber
        "POLICY_ID":    {"color": "#DC2626"},  # red
        "AMOUNT":       {"color": "#7C3AED"},  # violet
        "REGULATION":   {"color": "#0891B2"},  # cyan
    }
}

EDGE_TYPES = {
    "AMENDS":     {"color": "#EF4444", "weight": 3, "animated": True},
    "SUPERSEDES": {"color": "#F97316", "weight": 3, "animated": True},
    "IMPLEMENTS": {"color": "#22C55E", "weight": 2},
    "REFERENCES": {"color": "#94A3B8", "weight": 1},
    "CONTRADICTS":{"color": "#DC2626", "weight": 3, "dashed": True},
    "DEPENDS_ON": {"color": "#A855F7", "weight": 2},
}
```

### Graph Serialization for React Flow

```python
# serializer.py — converts NetworkX → React Flow format
def serialize_for_frontend(G: nx.DiGraph, focus_doc_id: str = None) -> dict:
    nodes = []
    edges = []
    
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "type": "knowledgeNode",    # custom React Flow node type
            "data": {
                "label": data["label"],
                "nodeType": data["type"],
                "metadata": data.get("metadata", {}),
                "isHighlighted": node_id == focus_doc_id
            },
            "position": compute_layout_position(G, node_id)  # use nx.spring_layout
        })
    
    for source, target, data in G.edges(data=True):
        edges.append({
            "id": f"{source}--{target}",
            "source": source,
            "target": target,
            "type": "smoothstep",
            "animated": data.get("relation_label") in ["AMENDS", "SUPERSEDES"],
            "label": data.get("relation_label"),
            "style": {"stroke": EDGE_COLORS[data.get("relation_label", "RELATES_TO")]}
        })
    
    return {"nodes": nodes, "edges": edges}
```

---

## Query & Answer Generation

### Grounded Answer Format

```python
class GroundedAnswer(BaseModel):
    answer: str                    # the direct answer
    confidence: float              # 0-1
    citations: List[Citation]      # source chunks
    reasoning_trace: str           # why these sources were chosen
    related_documents: List[str]   # doc IDs surfaced by graph traversal
    
class Citation(BaseModel):
    doc_id: str
    doc_title: str
    doc_type: str
    chunk_content: str             # exact text quoted
    page_num: Optional[int]
    relevance_score: float
    highlight_text: str            # substring to highlight in UI
```

**This is what makes answers enterprise-grade.** Every answer is traceable to exact source text with page numbers. Judges will click on citations. Make them work.

### RAG Prompt

```python
ANSWER_GENERATION_PROMPT = """
You are an enterprise knowledge intelligence system for government document analysis.

USER QUERY: {query}

RETRIEVED CONTEXT (in order of relevance):
{formatted_chunks}

RELATED DOCUMENTS (from knowledge graph traversal):
{related_doc_summaries}

Instructions:
1. Answer the query precisely using ONLY the provided context
2. For every factual claim, cite the specific document and page number
3. If context is insufficient, state what is missing — do not hallucinate
4. If documents contradict each other, highlight the contradiction
5. Format: direct answer first, then supporting evidence

Output format:
- answer: [your answer]
- citations: [list of source chunks used]
- gaps: [what information is missing, if any]
- contradictions: [any conflicting information found]
"""
```

---

## API Contract

```
POST   /api/ingest/upload              → Upload file, start async pipeline
GET    /api/ingest/{doc_id}/stream     → SSE: pipeline progress events
GET    /api/documents                  → List all documents (paginated)
GET    /api/documents/{doc_id}         → Document detail + entities
GET    /api/documents/{doc_id}/chunks  → Document chunks (for citation UI)

POST   /api/query                      → Semantic query → grounded answer
GET    /api/query/history              → Query history

GET    /api/graph                      → Full knowledge graph (React Flow format)
GET    /api/graph/{doc_id}/subgraph    → Focus graph for one document
GET    /api/graph/entities             → Entity node list
POST   /api/graph/refresh              → Trigger graph rebuild

GET    /api/health                     → Health + system stats
```

---

## Frontend Architecture

### Page Layout

```
AppShell (sidebar + topbar)
├── IngestPage       → drag-drop upload + real-time SSE progress
├── ExplorerPage     → document list, filters, entity panel, chronology
├── GraphPage        → full React Flow canvas (THE HERO VIEW)
└── QueryPage        → split: search panel | answer + citations
```

### React Flow Graph (The Demo Centerpiece)

```tsx
// KnowledgeGraph.tsx — key interactions
const KnowledgeGraph = () => {
  // 1. Click a node → focus view + highlight connected edges
  // 2. Click an edge → show relationship evidence in side panel
  // 3. Filter by doc type → hide/show node categories
  // 4. Filter by relationship type → isolate AMENDS, CONTRADICTS etc
  // 5. Search node → zoom-to-node animation
  // 6. Double-click document node → open document detail drawer
  // 7. Mini-map in bottom-right corner (built-in React Flow)
  // 8. Timeline mode toggle → switch to chronological layout
}
```

> [!IMPORTANT]
> The Knowledge Graph is your **demo moment**. When you upload 5 documents and the graph auto-populates with animated edges showing AMENDS and SUPERSEDES relationships — that's the demo clip that wins hackathons and goes on LinkedIn. Invest here.

### Zustand Store Shape

```typescript
interface AppStore {
  // Documents
  documents: Document[];
  selectedDocId: string | null;
  
  // Graph
  graphData: { nodes: FlowNode[], edges: FlowEdge[] };
  graphFilter: { docTypes: string[], relationTypes: string[] };
  
  // Query
  queryHistory: QueryResult[];
  activeQuery: QueryResult | null;
  
  // UI State
  ingestionJobs: Record<string, IngestionJob>;  // doc_id → job status
}
```

---

## Execution Phases

### Phase 1 — Foundation (Day 1)
**Goal**: Ingest works end-to-end. One document goes in, chunks + embeddings come out.

- [ ] FastAPI project setup, CORS, health endpoint
- [ ] SQLite schema + SQLAlchemy models
- [ ] ChromaDB initialization
- [ ] PDF upload endpoint + PyMuPDF extraction
- [ ] Semantic chunking
- [ ] Gemini embedding pipeline
- [ ] Basic vector search
- [ ] React frontend scaffold (Vite + Tailwind)
- [ ] Upload UI with drag-drop
- [ ] SSE progress streaming

**Ship criteria**: Upload a PDF → see it indexed → ask it a question → get an answer with citation.

---

### Phase 2 — Intelligence (Day 2)
**Goal**: Entity extraction + knowledge graph operational.

- [ ] Gemini entity extraction pipeline
- [ ] Document classifier
- [ ] Relationship detection (cross-document)
- [ ] NetworkX graph builder
- [ ] Graph API endpoints
- [ ] React Flow graph visualization
- [ ] Custom node/edge types
- [ ] Document Explorer with entity panel
- [ ] Query page with citation drawer

**Ship criteria**: Upload 5 documents → graph populates → can see AMENDS/REFERENCES edges → click edge to see evidence.

---

### Phase 3 — Polish (Day 3)
**Goal**: Demo-ready. Visual excellence. Zero rough edges.

- [ ] Hybrid retrieval (add SQLite FTS5)
- [ ] Graph layout improvements (temporal layout option)
- [ ] Contradiction detection highlighting
- [ ] Document timeline / chronology view
- [ ] Query history sidebar
- [ ] Animated ingestion progress (stage-by-stage)
- [ ] Performance: batch embedding, async pipeline
- [ ] Error states, loading skeletons, empty states
- [ ] Demo data: pre-load 5-8 gov documents
- [ ] README + deployment instructions

**Ship criteria**: A non-technical person can demo this in 3 minutes and it looks impressive.

---

## Demo Strategy — Hackathon Optimization

### Pre-load Demo Data
Don't rely on live uploads during the demo. Pre-process 6-8 documents:
- 2 policy documents (one AMENDS the other)  
- 2 scheme documents (one IMPLEMENTS a policy)
- 1 compliance report (REFERENCES multiple policies)
- 1 circular (SUPERSEDES a policy)
- 1 contract (DEPENDS_ON a scheme)

This guarantees a rich graph on first load.

### Demo Script (3 minutes)
```
0:00 - Show empty system, explain what it is (10s)
0:10 - Drag-drop 6 documents → watch SSE pipeline tick through stages
0:45 - Graph view auto-populates → zoom in on AMENDS edge → click it → see evidence quote
1:15 - Ask "Which policies have been superseded since 2023?" → watch grounded answer with citations
1:45 - Click citation → highlight in source document
2:00 - Show entity panel: all organizations, all policy IDs, all amounts extracted
2:20 - Ask "Are there any contradictions between these procurement policies?"
2:45 - Show contradiction highlighted in graph (red dashed edge)
3:00 - Conclude
```

### What Judges Are Actually Looking For
1. **Does it work?** (not crash in demo) — solved by pre-loaded data
2. **Is the AI actually doing something non-trivial?** — relationship detection answers this
3. **Is the UI impressive?** — React Flow graph is your visual money shot
4. **Is it actually useful for real problems?** — gov doc intelligence is a real pain point
5. **Could this scale?** — your architecture answer + SQLite→Weaviate migration path

---

## Scalability Path (For Interviews/Judges)

| Component | Hackathon | Production |
|-----------|-----------|------------|
| Vector DB | ChromaDB (local) | Qdrant cluster / Weaviate |
| Graph DB | NetworkX + JSON | Neo4j / ArangoDB |
| Metadata | SQLite | PostgreSQL |
| Queue | In-process async | Celery + Redis |
| OCR | PyMuPDF + Gemini Vision | AWS Textract / Azure DI |
| Auth | None | JWT + RBAC |
| Deploy | `uvicorn` + Vite dev | Docker + Railway/Render |

---

## Resume / Interview Talking Points

**What you built:**
> "An autonomous document intelligence platform that ingests unstructured documents, performs semantic entity extraction using Gemini's multimodal APIs, constructs a knowledge graph of cross-document relationships using NetworkX, and serves grounded, citation-backed answers through a hybrid vector + BM25 retrieval pipeline — all visualized through a React Flow graph interface."

**What was technically hard:**
- Cross-document relationship detection without O(n²) blowup (entity-overlap filtering)
- Semantic chunking that respects document structure (vs. naive sliding window)
- Grounded answer generation with exact chunk citation tracing
- Real-time pipeline progress streaming via SSE with stage-level granularity

**What would you do differently at scale:**
- Replace ChromaDB with Qdrant for horizontal scaling
- Replace synchronous pipeline with Celery task queue for parallel document processing
- Add graph database (Neo4j) for complex multi-hop relationship queries
- Add RBAC for multi-tenant document isolation

---

## Open Questions Requiring Your Input

> [!IMPORTANT]
> **Gemini API Key**: Do you have a Gemini API key with access to `gemini-1.5-flash` and `gemini-1.5-pro`? The embedding model needed is `text-embedding-004`. Confirm access before architecting around it.

> [!IMPORTANT]
> **Demo Documents**: Do you have real government documents for the demo, or do I need to source/generate synthetic ones? The quality of demo data is directly correlated with demo quality.

> [!IMPORTANT]
> **Timeline**: How many days do you have? This plan is scoped for 3 days. If you have 1 day, Phase 1 only + basic graph. If you have 5+ days, we add multi-user, RBAC, and production deployment.

> [!NOTE]
> **React Flow License**: React Flow is MIT-licensed for the base library. The Pro version has additional components. The free version is sufficient for everything described here.

> [!NOTE]
> **Tailwind vs Vanilla CSS**: You specified Tailwind in your stack. Confirmed we'll use Tailwind + shadcn/ui for components. This is the right call for hackathon speed.
