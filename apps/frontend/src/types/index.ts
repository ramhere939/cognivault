// ─────────────────────────────────────────────────────────────────
// Shared TypeScript types — mirrors backend Pydantic schemas
// ─────────────────────────────────────────────────────────────────

export type DocType =
  | 'policy' | 'invoice' | 'contract' | 'circular'
  | 'meeting_note' | 'scheme' | 'compliance' | 'procurement' | 'unknown';

export type DocStatus = 'processing' | 'ocr' | 'classify' | 'chunk' | 'embed' | 'extract' | 'graph' | 'indexed' | 'failed';

export type EntityType = 'PERSON' | 'ORG' | 'DATE' | 'AMOUNT' | 'POLICY_ID' | 'LOCATION' | 'REGULATION' | 'KEYWORD';

export type RelationLabel =
  | 'AMENDS' | 'SUPERSEDES' | 'IMPLEMENTS' | 'REFERENCES'
  | 'CONTRADICTS' | 'DEPENDS_ON' | 'RELATES_TO' | 'MENTIONS';

// ─── Documents ────────────────────────────────────────────────────
export interface Document {
  id: string;
  filename: string;
  doc_type: DocType;
  title?: string;
  summary?: string;
  doc_date?: string;
  author?: string;
  department?: string;
  status: DocStatus;
  page_count?: number;
  file_size?: number;
  created_at: string;
  indexed_at?: string;
  extra_metadata?: Record<string, unknown>;
}

export interface Entity {
  id: string;
  name: string;
  entity_type: EntityType;
  normalized?: string;
  evidence_quote?: string;
  confidence?: number;
}

export interface Chunk {
  id: string;
  doc_id: string;
  content: string;
  chunk_index: number;
  page_num?: number;
  section_header?: string;
}

export interface DocumentDetail extends Document {
  entities: Entity[];
  chunk_count: number;
}

// ─── Ingestion ────────────────────────────────────────────────────
export interface IngestionStartResponse {
  doc_id: string;
  filename: string;
  message: string;
  stream_url: string;
}

export interface ProgressEvent {
  stage: string;
  progress: number;
  message: string;
  doc_id: string;
  error?: string;
}

export interface IngestionJob {
  doc_id: string;
  filename: string;
  stage: string;
  progress: number;
  message: string;
  error?: string;
}

// ─── Query ────────────────────────────────────────────────────────
export interface Citation {
  doc_id: string;
  doc_title?: string;
  doc_type: DocType;
  chunk_id: string;
  chunk_content: string;
  page_num?: number;
  section_header?: string;
  relevance_score: number;
  highlight_text?: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  confidence: number;
  citations: Citation[];
  reasoning_trace?: string;
  related_doc_ids: string[];
  gaps?: string;
  contradictions?: string;
  processing_time_ms: number;
}

// ─── Graph ────────────────────────────────────────────────────────
export interface GraphNodeData {
  label: string;
  nodeType: string;
  docType?: string;
  department?: string;
  date?: string;
  summary?: string;
  status?: string;
  isHighlighted: boolean;
  metadata: {
    color?: string;
    confidence?: number;
  };
}

export interface GraphNode {
  id: string;
  type: string;
  data: GraphNodeData;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  animated: boolean;
  label?: string;
  data: {
    relation_label: string;
    confidence: number;
    evidence_quote?: string;
    explanation?: string;
  };
  style: { stroke?: string; strokeWidth?: number };
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: Record<string, unknown>;
}

// ─── Stats ────────────────────────────────────────────────────────
export interface SystemStats {
  total_docs: number;
  indexed: number;
  processing: number;
  failed: number;
  total_chunks: number;
  total_entities: number;
  total_relationships: number;
}
