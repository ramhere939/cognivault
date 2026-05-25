import { create } from 'zustand';
import type {
  Document, QueryResponse, GraphNode, GraphEdge, IngestionJob, SystemStats,
} from '@/types';

interface AppState {
  // ── Documents ─────────────────────────────────────────────────
  documents: Document[];
  selectedDocId: string | null;
  stats: SystemStats | null;
  setDocuments: (docs: Document[]) => void;
  setSelectedDoc: (id: string | null) => void;
  setStats: (stats: SystemStats) => void;
  upsertDocument: (doc: Document) => void;

  // ── Ingestion Jobs ────────────────────────────────────────────
  ingestionJobs: Record<string, IngestionJob>;
  upsertJob: (job: IngestionJob) => void;
  removeJob: (docId: string) => void;

  // ── Graph ─────────────────────────────────────────────────────
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  graphLoading: boolean;
  selectedEdge: GraphEdge | null;
  setGraph: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  setGraphLoading: (v: boolean) => void;
  setSelectedEdge: (edge: GraphEdge | null) => void;

  // ── Query ─────────────────────────────────────────────────────
  queryHistory: QueryResponse[];
  activeQuery: QueryResponse | null;
  queryLoading: boolean;
  addQueryResult: (result: QueryResponse) => void;
  setActiveQuery: (result: QueryResponse | null) => void;
  setQueryLoading: (v: boolean) => void;

  // ── UI ────────────────────────────────────────────────────────
  sidebarOpen: boolean;
  activePage: 'ingest' | 'graph' | 'query' | 'explorer' | 'alerts';
  setSidebarOpen: (v: boolean) => void;
  setActivePage: (page: AppState['activePage']) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Documents
  documents: [],
  selectedDocId: null,
  stats: null,
  setDocuments: (documents) => set({ documents }),
  setSelectedDoc: (id) => set({ selectedDocId: id }),
  setStats: (stats) => set({ stats }),
  upsertDocument: (doc) => set((state) => {
    const idx = state.documents.findIndex(d => d.id === doc.id);
    if (idx >= 0) {
      const docs = [...state.documents];
      docs[idx] = doc;
      return { documents: docs };
    }
    return { documents: [doc, ...state.documents] };
  }),

  // Ingestion
  ingestionJobs: {},
  upsertJob: (job) => set((state) => ({
    ingestionJobs: { ...state.ingestionJobs, [job.doc_id]: job },
  })),
  removeJob: (docId) => set((state) => {
    const jobs = { ...state.ingestionJobs };
    delete jobs[docId];
    return { ingestionJobs: jobs };
  }),

  // Graph
  graphNodes: [],
  graphEdges: [],
  graphLoading: false,
  selectedEdge: null,
  setGraph: (graphNodes, graphEdges) => set({ graphNodes, graphEdges }),
  setGraphLoading: (graphLoading) => set({ graphLoading }),
  setSelectedEdge: (selectedEdge) => set({ selectedEdge }),

  // Query
  queryHistory: [],
  activeQuery: null,
  queryLoading: false,
  addQueryResult: (result) => set((state) => ({
    queryHistory: [result, ...state.queryHistory.slice(0, 19)],
    activeQuery: result,
  })),
  setActiveQuery: (activeQuery) => set({ activeQuery }),
  setQueryLoading: (queryLoading) => set({ queryLoading }),

  // UI
  sidebarOpen: true,
  activePage: 'ingest',
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setActivePage: (activePage) => set({ activePage }),
}));
