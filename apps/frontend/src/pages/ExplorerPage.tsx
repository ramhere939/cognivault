import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText, Search, Filter, Trash2, ChevronRight,
  User, Building2, Hash, DollarSign, Scale, Calendar,
  MapPin, Tag, RefreshCw, Eye,
} from 'lucide-react';
import { documentsApi } from '@/api/client';
import { useAppStore } from '@/store/useAppStore';
import type { Document, DocumentDetail, Entity } from '@/types';

const DOC_TYPES = ['policy','invoice','contract','circular','scheme','compliance','procurement','meeting_note'];

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  PERSON:     <User size={11} />,
  ORG:        <Building2 size={11} />,
  POLICY_ID:  <Hash size={11} />,
  AMOUNT:     <DollarSign size={11} />,
  DATE:       <Calendar size={11} />,
  REGULATION: <Scale size={11} />,
  LOCATION:   <MapPin size={11} />,
  KEYWORD:    <Tag size={11} />,
};

const ENTITY_COLORS: Record<string, string> = {
  PERSON:     '#059669',
  ORG:        '#D97706',
  POLICY_ID:  '#DC2626',
  AMOUNT:     '#7C3AED',
  DATE:       '#0891B2',
  REGULATION: '#0E7490',
  LOCATION:   '#65A30D',
  KEYWORD:    '#6B7280',
};

// ─── Document List Item ───────────────────────────────────────────
function DocItem({
  doc,
  selected,
  onClick,
}: { doc: Document; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all duration-150 border ${
        selected
          ? 'bg-brand-600/15 border-brand-500/30 shadow-glow-brand'
          : 'bg-surface-700/30 border-transparent hover:border-white/10 hover:bg-surface-600/30'
      }`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
        selected ? 'bg-brand-600/30' : 'bg-surface-600/60'
      }`}>
        <FileText size={14} className={selected ? 'text-brand-300' : 'text-slate-500'} />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-slate-200 leading-tight truncate">
          {doc.title || doc.filename}
        </p>
        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
          <span className={`badge badge-${doc.doc_type}`}>{doc.doc_type}</span>
          <span className={`badge badge-${doc.status}`}>{doc.status}</span>
          {doc.department && (
            <span className="text-[9px] text-slate-600 truncate max-w-[100px]">{doc.department}</span>
          )}
        </div>
        {doc.doc_date && (
          <p className="text-[10px] text-slate-600 mt-1">{doc.doc_date}</p>
        )}
      </div>

      <ChevronRight size={13} className={`flex-shrink-0 mt-1 ${selected ? 'text-brand-400' : 'text-slate-600'}`} />
    </button>
  );
}

// ─── Entity Badge ─────────────────────────────────────────────────
function EntityBadge({ entity }: { entity: Entity }) {
  const color = ENTITY_COLORS[entity.entity_type] || '#6b7280';
  const [showEvidence, setShowEvidence] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setShowEvidence(!showEvidence)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs border transition-all hover:scale-[1.02]"
        style={{
          background: `${color}12`,
          borderColor: `${color}30`,
          color: `${color}dd`,
        }}
        title={entity.evidence_quote || ''}
      >
        <span style={{ color }}>{ENTITY_ICONS[entity.entity_type]}</span>
        <span className="font-medium truncate max-w-[120px]">{entity.normalized || entity.name}</span>
        {entity.confidence && (
          <span className="text-[9px] opacity-60 font-mono">{Math.round(entity.confidence * 100)}%</span>
        )}
      </button>
      {showEvidence && entity.evidence_quote && (
        <div className="absolute top-full left-0 mt-1 z-20 w-64 card p-2.5 border border-white/10 shadow-panel animate-fade-in">
          <p className="text-[9px] text-slate-500 mb-1 uppercase tracking-wider font-semibold">Evidence</p>
          <p className="text-[11px] text-slate-300 italic leading-relaxed">"{entity.evidence_quote}"</p>
        </div>
      )}
    </div>
  );
}

// ─── Document Detail Panel ────────────────────────────────────────
function DocDetailPanel({ docId }: { docId: string }) {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const { setActivePage, setSelectedEdge } = useAppStore();

  useEffect(() => {
    setLoading(true);
    documentsApi.get(docId)
      .then(setDetail)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [docId]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw size={18} className="animate-spin text-brand-400" />
      </div>
    );
  }

  if (!detail) return null;

  // Group entities by type
  const entitiesByType = detail.entities.reduce((acc, e) => {
    if (!acc[e.entity_type]) acc[e.entity_type] = [];
    acc[e.entity_type].push(e);
    return acc;
  }, {} as Record<string, Entity[]>);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 animate-fade-in">
      {/* Document header */}
      <div className="card p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h2 className="text-sm font-bold text-white leading-tight">
            {detail.title || detail.filename}
          </h2>
          <span className={`badge badge-${detail.doc_type} flex-shrink-0`}>{detail.doc_type}</span>
        </div>

        {detail.summary && (
          <p className="text-xs text-slate-400 leading-relaxed mb-3">{detail.summary}</p>
        )}

        <div className="grid grid-cols-2 gap-2 text-[10px]">
          {detail.author && (
            <div>
              <span className="text-slate-600">Author</span>
              <p className="text-slate-300 font-medium">{detail.author}</p>
            </div>
          )}
          {detail.department && (
            <div>
              <span className="text-slate-600">Department</span>
              <p className="text-slate-300 font-medium">{detail.department}</p>
            </div>
          )}
          {detail.doc_date && (
            <div>
              <span className="text-slate-600">Date</span>
              <p className="text-slate-300 font-medium">{detail.doc_date}</p>
            </div>
          )}
          <div>
            <span className="text-slate-600">Pages</span>
            <p className="text-slate-300 font-medium">{detail.page_count || '—'}</p>
          </div>
          <div>
            <span className="text-slate-600">Chunks</span>
            <p className="text-slate-300 font-medium">{detail.chunk_count}</p>
          </div>
          <div>
            <span className="text-slate-600">Entities</span>
            <p className="text-slate-300 font-medium">{detail.entities.length}</p>
          </div>
        </div>

        {/* Keywords */}
        {detail.extra_metadata?.keywords && Array.isArray(detail.extra_metadata.keywords) && (
          <div className="mt-3 flex flex-wrap gap-1">
            {(detail.extra_metadata.keywords as string[]).map(kw => (
              <span key={kw} className="px-1.5 py-0.5 bg-surface-600/60 rounded text-[10px] text-slate-500 border border-white/5">
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Entities */}
      {Object.entries(entitiesByType).map(([type, entities]) => (
        <div key={type} className="card p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <span style={{ color: ENTITY_COLORS[type] }}>{ENTITY_ICONS[type]}</span>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{type}</span>
            <span className="ml-auto text-[10px] text-slate-600">{entities.length}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {entities.map(e => (
              <EntityBadge key={e.id} entity={e} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Explorer Page ────────────────────────────────────────────────
export function ExplorerPage() {
  const { documents, selectedDocId, setSelectedDoc, setDocuments } = useAppStore();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const docs = await documentsApi.list({ doc_type: typeFilter || undefined });
      setDocuments(docs);
    } finally {
      setLoading(false);
    }
  }, [typeFilter, setDocuments]);

  useEffect(() => { refresh(); }, [typeFilter]);

  const filtered = documents.filter(d =>
    !search ||
    (d.title || d.filename).toLowerCase().includes(search.toLowerCase()) ||
    d.department?.toLowerCase().includes(search.toLowerCase()) ||
    d.doc_type.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = async (e: React.MouseEvent, docId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this document? This cannot be undone.')) return;
    await documentsApi.delete(docId);
    setDocuments(documents.filter(d => d.id !== docId));
    if (selectedDocId === docId) setSelectedDoc(null);
  };

  return (
    <div className="h-full flex">
      {/* Doc list */}
      <div className="w-80 flex-shrink-0 border-r border-white/5 flex flex-col">
        {/* Filters */}
        <div className="p-3 border-b border-white/5 space-y-2">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search documents..."
              className="input pl-8 text-xs"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
              className="input text-xs flex-1"
            >
              <option value="">All types</option>
              {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={refresh} className="btn-ghost px-2" disabled={loading}>
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Stats bar */}
        <div className="px-3 py-1.5 border-b border-white/5 flex items-center gap-2">
          <span className="text-[10px] text-slate-600">{filtered.length} documents</span>
          <div className="ml-auto flex gap-1">
            {['indexed', 'processing', 'failed'].map(s => {
              const count = filtered.filter(d => d.status === s).length;
              if (!count) return null;
              return (
                <span key={s} className={`badge badge-${s}`}>{count}</span>
              );
            })}
          </div>
        </div>

        {/* Document list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-center">
              <FileText size={24} className="text-slate-700 mb-2" />
              <p className="text-xs text-slate-600">No documents found</p>
            </div>
          ) : (
            filtered.map(doc => (
              <div key={doc.id} className="group relative">
                <DocItem
                  doc={doc}
                  selected={selectedDocId === doc.id}
                  onClick={() => setSelectedDoc(doc.id)}
                />
                <button
                  onClick={(e) => handleDelete(e, doc.id)}
                  className="absolute top-2 right-6 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:text-red-400 text-slate-600"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Detail panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedDocId ? (
          <>
            {/* Detail header */}
            <div className="px-4 py-3 border-b border-white/5 bg-surface-800/30 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Document Detail</span>
            </div>
            <DocDetailPanel docId={selectedDocId} />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60">
            <Eye size={32} className="text-slate-600 mb-3" />
            <p className="text-slate-500 text-sm">Select a document to inspect</p>
            <p className="text-slate-600 text-xs mt-1">View entities, summary, and metadata</p>
          </div>
        )}
      </div>
    </div>
  );
}
