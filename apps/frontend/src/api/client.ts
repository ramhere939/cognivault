import axios from 'axios';
import type {
  Document, DocumentDetail, Chunk,
  IngestionStartResponse,
  QueryResponse,
  GraphResponse,
  SystemStats,
} from '@/types';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 60_000,
});

// ─── Documents ───────────────────────────────────────────────────
export const documentsApi = {
  list: (params?: { doc_type?: string; status?: string }) =>
    api.get<Document[]>('/documents', { params }).then(r => r.data),

  stats: () =>
    api.get<SystemStats>('/documents/stats').then(r => r.data),

  get: (id: string) =>
    api.get<DocumentDetail>(`/documents/${id}`).then(r => r.data),

  chunks: (id: string) =>
    api.get<Chunk[]>(`/documents/${id}/chunks`).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/documents/${id}`).then(r => r.data),
};

// ─── Ingest ──────────────────────────────────────────────────────
export const ingestApi = {
  upload: (file: File): Promise<IngestionStartResponse> => {
    const form = new FormData();
    form.append('file', file);
    return api.post<IngestionStartResponse>('/ingest/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
};

// ─── Query ───────────────────────────────────────────────────────
export const queryApi = {
  query: (payload: { query: string; doc_type_filter?: string; top_k?: number }) =>
    api.post<QueryResponse>('/query', payload).then(r => r.data),
};

// ─── Graph ───────────────────────────────────────────────────────
export const graphApi = {
  full: (hideMentions = true) =>
    api.get<GraphResponse>('/graph', { params: { hide_mentions: hideMentions } }).then(r => r.data),

  subgraph: (docId: string, depth = 2) =>
    api.get<GraphResponse>(`/graph/${docId}/subgraph`, { params: { depth } }).then(r => r.data),

  stats: () =>
    api.get<Record<string, unknown>>('/graph/stats').then(r => r.data),
};

export default api;
