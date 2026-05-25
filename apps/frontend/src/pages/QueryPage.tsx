import React, { useState, useRef, useCallback } from 'react';
import {
  Search, Send, FileText, ChevronDown, ChevronUp,
  AlertTriangle, Clock, Zap, BookOpen, ExternalLink,
} from 'lucide-react';
import { queryApi } from '@/api/client';
import { useAppStore } from '@/store/useAppStore';
import type { QueryResponse, Citation } from '@/types';

// ─── Confidence Indicator ─────────────────────────────────────────
function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 75 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-surface-600 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono" style={{ color }}>{pct}%</span>
    </div>
  );
}

// ─── Citation Card ────────────────────────────────────────────────
function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const DOC_TYPE_COLORS: Record<string, string> = {
    policy: '#6366f1', invoice: '#f59e0b', contract: '#22c55e',
    circular: '#06b6d4', scheme: '#a855f7', compliance: '#f43f5e',
    procurement: '#f97316', meeting_note: '#38bdf8',
  };
  const color = DOC_TYPE_COLORS[citation.doc_type] || '#6b7280';

  return (
    <div className="card border border-white/5 overflow-hidden">
      <button
        className="w-full flex items-start gap-3 p-3 text-left hover:bg-white/3 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <span
          className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5"
          style={{ background: `${color}25`, color }}
        >
          {index}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-slate-200 truncate">
              {citation.doc_title || 'Untitled'}
            </span>
            <span className={`badge badge-${citation.doc_type}`}>{citation.doc_type}</span>
            {citation.page_num && (
              <span className="text-[10px] text-slate-500">p.{citation.page_num}</span>
            )}
          </div>
          {citation.section_header && (
            <p className="text-[10px] text-slate-500 mt-0.5 truncate">§ {citation.section_header}</p>
          )}
          <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 italic">
            "{citation.highlight_text || citation.chunk_content.slice(0, 120)}"
          </p>
        </div>
        <div className="flex-shrink-0 flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500">
            {Math.round(citation.relevance_score * 100)}%
          </span>
          {expanded ? <ChevronUp size={12} className="text-slate-500" /> : <ChevronDown size={12} className="text-slate-500" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-white/5 pt-3 animate-fade-in">
          <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
            {citation.chunk_content}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Answer Card ──────────────────────────────────────────────────
function AnswerCard({ result }: { result: QueryResponse }) {
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Answer */}
      <div className="card p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-brand-400" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Answer</span>
          </div>
          <div className="flex items-center gap-3">
            <ConfidenceBar value={result.confidence} />
            <span className="text-[10px] text-slate-600 font-mono">{result.processing_time_ms}ms</span>
          </div>
        </div>

        <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{result.answer}</p>

        {result.contradictions && (
          <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex gap-2">
            <AlertTriangle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-red-400 mb-0.5">Contradiction Detected</p>
              <p className="text-xs text-red-300/80">{result.contradictions}</p>
            </div>
          </div>
        )}

        {result.gaps && (
          <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-xs font-semibold text-amber-400 mb-0.5">Information Gaps</p>
            <p className="text-xs text-amber-300/80">{result.gaps}</p>
          </div>
        )}
      </div>

      {/* Reasoning trace */}
      {result.reasoning_trace && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen size={13} className="text-slate-500" />
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Reasoning Trace</span>
          </div>
          <p className="text-xs text-slate-500 italic">{result.reasoning_trace}</p>
        </div>
      )}

      {/* Citations */}
      {result.citations.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <ExternalLink size={13} className="text-slate-500" />
            <span className="text-xs font-semibold text-slate-400">
              Sources ({result.citations.length})
            </span>
          </div>
          <div className="space-y-2">
            {result.citations.map((c, i) => (
              <CitationCard key={c.chunk_id} citation={c} index={i + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Query Page ───────────────────────────────────────────────────
const EXAMPLE_QUERIES = [
  'Which policies have been amended or superseded?',
  'What are the key financial obligations in procurement contracts?',
  'Summarize the compliance requirements across all documents',
  'Are there any contradictions between the scheme documents?',
];

export function QueryPage() {
  const [query, setQuery] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const { queryLoading, setQueryLoading, activeQuery, addQueryResult, queryHistory } = useAppStore();

  const handleQuery = useCallback(async (q: string) => {
    if (!q.trim() || queryLoading) return;
    setQueryLoading(true);
    try {
      const result = await queryApi.query({
        query: q.trim(),
        doc_type_filter: docTypeFilter || undefined,
        top_k: 5,
      });
      addQueryResult(result);
    } catch (err) {
      console.error('Query failed:', err);
    } finally {
      setQueryLoading(false);
    }
  }, [queryLoading, docTypeFilter, addQueryResult, setQueryLoading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery(query);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/5 bg-surface-800/50 backdrop-blur-sm">
        <h1 className="text-base font-bold text-white">Knowledge Query</h1>
        <p className="text-xs text-slate-500">Ask anything — answers are grounded and cited to source documents</p>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Query + Results */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Query input */}
          <div className="p-4 border-b border-white/5">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your knowledge base..."
                  className="input pl-9 pr-4"
                  disabled={queryLoading}
                />
              </div>
              <select
                value={docTypeFilter}
                onChange={e => setDocTypeFilter(e.target.value)}
                className="input w-36 text-xs"
              >
                <option value="">All types</option>
                {['policy','invoice','contract','circular','scheme','compliance','procurement','meeting_note'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <button
                onClick={() => handleQuery(query)}
                disabled={!query.trim() || queryLoading}
                className="btn-primary"
              >
                {queryLoading ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Send size={14} />
                )}
                Ask
              </button>
            </div>

            {/* Example queries */}
            {!activeQuery && (
              <div className="mt-3 flex flex-wrap gap-2">
                {EXAMPLE_QUERIES.map(eq => (
                  <button
                    key={eq}
                    onClick={() => { setQuery(eq); handleQuery(eq); }}
                    className="text-xs px-3 py-1.5 bg-surface-600/50 hover:bg-surface-500/50 border border-white/5 hover:border-brand-500/30 text-slate-400 hover:text-slate-200 rounded-lg transition-all"
                  >
                    {eq}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Answer */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeQuery ? (
              <AnswerCard result={activeQuery} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center opacity-60">
                <Search size={36} className="text-slate-600 mb-3" />
                <p className="text-slate-500 text-sm">Ask a question to get started</p>
                <p className="text-slate-600 text-xs mt-1">Answers include citations traceable to source pages</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Query history */}
        {queryHistory.length > 1 && (
          <div className="w-64 border-l border-white/5 flex flex-col bg-surface-800/30">
            <div className="px-3 py-3 border-b border-white/5">
              <div className="flex items-center gap-1.5">
                <Clock size={12} className="text-slate-500" />
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">History</span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {queryHistory.map((result, i) => (
                <button
                  key={i}
                  onClick={() => useAppStore.getState().setActiveQuery(result)}
                  className={`w-full text-left p-2.5 rounded-lg text-xs transition-all ${
                    result === activeQuery
                      ? 'bg-brand-600/20 border border-brand-500/30 text-brand-300'
                      : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                  }`}
                >
                  <p className="line-clamp-2 leading-relaxed">{result.query}</p>
                  <p className="text-[10px] text-slate-600 mt-1">{result.citations.length} citations</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
