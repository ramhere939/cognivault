import React, { useCallback, useEffect, useState, memo } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, BackgroundVariant,
  type NodeProps, type EdgeProps, getBezierPath,
  BaseEdge, EdgeLabelRenderer, Handle, Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  RefreshCw, Filter, X, FileText, User, Building2,
  Hash, DollarSign, Scale, MapPin, Tag, Flame, Calendar
} from 'lucide-react';
import { api, graphApi } from '@/api/client';
import { useAppStore } from '@/store/useAppStore';
import type { GraphEdge as AppEdge } from '@/types';

// ─── Node type icons ──────────────────────────────────────────────
const NODE_ICONS: Record<string, React.ReactNode> = {
  DOCUMENT:   <FileText size={12} />,
  PERSON:     <User size={12} />,
  ORG:        <Building2 size={12} />,
  POLICY_ID:  <Hash size={12} />,
  AMOUNT:     <DollarSign size={12} />,
  REGULATION: <Scale size={12} />,
  LOCATION:   <MapPin size={12} />,
  KEYWORD:    <Tag size={12} />,
};

// ─── Custom Knowledge Node ────────────────────────────────────────
const KnowledgeNode = memo(({ data }: NodeProps) => {
  const nodeData = data as {
    label: string; nodeType: string; docType?: string;
    department?: string; date?: string; isHighlighted: boolean;
    metadata: { color?: string };
  };
  const color = nodeData.metadata?.color || '#6366f1';
  const isDoc = nodeData.nodeType === 'DOCUMENT';

  return (
    <div
      className={`
        relative rounded-xl border transition-all duration-200 cursor-pointer
        ${isDoc ? 'min-w-[140px] max-w-[180px]' : 'min-w-[100px] max-w-[140px]'}
        ${nodeData.isHighlighted ? 'scale-105' : ''}
      `}
      style={{
        background: `linear-gradient(135deg, ${color}18, ${color}08)`,
        borderColor: `${color}40`,
        boxShadow: nodeData.isHighlighted ? `0 0 24px ${color}50` : `0 4px 16px rgba(0,0,0,0.4)`,
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-1.5 px-2.5 py-2 rounded-t-xl border-b"
        style={{ borderColor: `${color}20`, background: `${color}15` }}
      >
        <span style={{ color }}>{NODE_ICONS[nodeData.nodeType] || <Tag size={12} />}</span>
        <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: `${color}cc` }}>
          {nodeData.nodeType === 'DOCUMENT' ? nodeData.docType || 'DOC' : nodeData.nodeType}
        </span>
      </div>

      {/* Label */}
      <div className="px-2.5 py-2">
        <p className="text-[11px] font-semibold text-slate-200 leading-tight line-clamp-2">
          {nodeData.label}
        </p>
        {isDoc && nodeData.department && (
          <p className="text-[9px] text-slate-500 mt-0.5 truncate">{nodeData.department}</p>
        )}
        {isDoc && nodeData.date && (
          <p className="text-[9px] text-slate-600 mt-0.5">{nodeData.date}</p>
        )}
      </div>

      {/* Glow dot */}
      {isDoc && (
        <div
          className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full animate-pulse-slow"
          style={{ background: color }}
        />
      )}

      {/* Invisible handles required for ReactFlow to draw edges */}
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  );
});
KnowledgeNode.displayName = 'KnowledgeNode';

// ─── Custom Edge with label ───────────────────────────────────────
function KnowledgeEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, data, style, label, markerEnd,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });
  const { setSelectedEdge } = useAppStore();

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <button
          className="absolute pointer-events-all nodrag nopan"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)` }}
          onClick={() => setSelectedEdge(data as AppEdge)}
        >
          {label && (
            <span
              className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider"
              style={{
                background: `${style?.stroke || '#6366f1'}20`,
                color: style?.stroke || '#6366f1',
                border: `1px solid ${style?.stroke || '#6366f1'}40`,
              }}
            >
              {String(label)}
            </span>
          )}
        </button>
      </EdgeLabelRenderer>
    </>
  );
}

// ─── Edge details panel ───────────────────────────────────────────
function EdgePanel() {
  const { selectedEdge, setSelectedEdge } = useAppStore();
  if (!selectedEdge) return null;

  const edge = selectedEdge as unknown as { data?: { relation_label?: string; confidence?: number; evidence_quote?: string; explanation?: string } };
  const edgeData = edge.data || {};

  const EDGE_COLORS: Record<string, string> = {
    SUPERSEDES: '#f97316', REVOKES: '#dc2626', AMENDS: '#eab308',
    ENABLES: '#10b981', MANDATED_BY: '#3b82f6', BLOCKS: '#ef4444',
    IMPLEMENTS: '#22c55e', PROCURES_UNDER: '#6366f1', REFERENCES: '#94a3b8',
    DUPLICATES: '#f43f5e', MENTIONS: '#cbd5e1', RELATES_TO: '#94a3b8',
  };
  const color = EDGE_COLORS[edgeData.relation_label || ''] || '#6366f1';

  return (
    <div className="absolute top-4 right-4 w-72 card p-4 z-10 animate-slide-in border border-white/10">
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-xs font-bold px-2 py-1 rounded-full"
          style={{ background: `${color}20`, color }}
        >
          {edgeData.relation_label}
        </span>
        <button onClick={() => setSelectedEdge(null)} className="btn-ghost p-1">
          <X size={14} />
        </button>
      </div>

      {edgeData.confidence && (
        <div className="mb-3">
          <p className="text-[10px] text-slate-500 mb-1">Confidence</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-surface-600 rounded-full h-1">
              <div
                className="h-full rounded-full"
                style={{ width: `${edgeData.confidence * 100}%`, background: color }}
              />
            </div>
            <span className="text-xs font-mono text-slate-300">{(edgeData.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}

      {edgeData.evidence_quote && (
        <div className="mb-3">
          <p className="text-[10px] text-slate-500 mb-1">Evidence</p>
          <blockquote className="text-xs text-slate-300 italic bg-surface-600/50 rounded-lg p-2.5 border-l-2" style={{ borderColor: color }}>
            "{edgeData.evidence_quote}"
          </blockquote>
        </div>
      )}

      {edgeData.explanation && (
        <div>
          <p className="text-[10px] text-slate-500 mb-1">Explanation</p>
          <p className="text-xs text-slate-400 leading-relaxed">{edgeData.explanation}</p>
        </div>
      )}
    </div>
  );
}

// ─── Main Graph Page ──────────────────────────────────────────────
const nodeTypes = { knowledgeNode: KnowledgeNode };
const edgeTypes = { smoothstep: KnowledgeEdge };

export function GraphPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Record<string, unknown>>({});
  const [hiddenEdgeTypes, setHiddenEdgeTypes] = useState<Set<string>>(new Set(['RELATES_TO', 'REFERENCES']));
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [showRiskHeatmap, setShowRiskHeatmap] = useState(false);
  const [riskNodes, setRiskNodes] = useState<Set<string>>(new Set());
  const [yearFilter, setYearFilter] = useState<string | null>(null);
  const { setSelectedEdge, activeQuery } = useAppStore();

  // Compute available years from nodes
  const availableYears = React.useMemo(() => {
    const years = new Set<string>();
    nodes.forEach((n: any) => {
      const d = n.data?.date;
      if (d) {
        const y = String(d).substring(0, 4);
        if (y.match(/^\d{4}$/)) years.add(y);
      }
    });
    return Array.from(years).sort().reverse();
  }, [nodes]);

  useEffect(() => {
    if (showRiskHeatmap) {
      api.get<{ alerts: { affected_doc_ids: string[] }[] }>('/alerts', { params: { resolved: false, page_size: 100 } })
        .then(r => {
          const atRisk = new Set<string>();
          r.data.alerts.forEach(a => a.affected_doc_ids.forEach(id => atRisk.add(id)));
          setRiskNodes(atRisk);
        })
        .catch(console.error);
    } else {
      setRiskNodes(new Set());
    }
  }, [showRiskHeatmap]);

  const loadGraph = useCallback(async (focusId: string | null = null) => {
    setLoading(true);
    try {
      let data;
      if (focusId) {
        data = (await api.get(`/graph/${focusId}/subgraph`)).data;
      } else {
        data = await graphApi.full(false);
      }
      setNodes(data.nodes as unknown as Parameters<typeof setNodes>[0]);
      setEdges(data.edges as unknown as Parameters<typeof setEdges>[0]);
      if (!focusId) setStats(data.stats);
    } catch (err) {
      console.error('Failed to load graph:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph(focusedNodeId);
  }, [loadGraph, focusedNodeId]);

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-surface-800/50 backdrop-blur-sm">
        <div>
          <h1 className="text-base font-bold text-white flex items-center gap-2">
            Knowledge Graph
            {focusedNodeId && (
              <>
                <span className="text-slate-500">/</span>
                <span className="text-brand-400 text-sm bg-brand-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                  Focus View
                  <button onClick={() => setFocusedNodeId(null)} className="hover:text-white ml-1">
                    <X size={12} />
                  </button>
                </span>
              </>
            )}
          </h1>
          <p className="text-xs text-slate-500">
            {nodes.length} nodes · {edges.length} edges
            {stats.document_count && !focusedNodeId ? ` · ${stats.document_count as number} documents` : ''}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Edge Filter Dropdown / Panel (simplified as toggles) */}
          <div className="hidden md:flex items-center gap-2 mr-2 bg-surface-700/50 px-2 py-1 rounded-lg border border-white/5">
            <Filter size={14} className="text-slate-400" />
            {[
              { label: 'SUPERSEDES', color: '#f97316' },
              { label: 'IMPLEMENTS', color: '#22c55e' },
              { label: 'ENABLES', color: '#10b981' },
              { label: 'BLOCKS', color: '#ef4444' },
            ].map(({ label, color }) => {
              const isHidden = hiddenEdgeTypes.has(label);
              return (
                <button
                  key={label}
                  onClick={() => {
                    const next = new Set(hiddenEdgeTypes);
                    if (isHidden) next.delete(label);
                    else next.add(label);
                    setHiddenEdgeTypes(next);
                  }}
                  className={`flex items-center gap-1 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded transition-all ${
                    isHidden ? 'opacity-40 grayscale hover:opacity-70' : 'bg-surface-600/40'
                  }`}
                  style={{ color }}
                >
                  <span className="w-2 h-0.5 rounded" style={{ background: color }} />
                  {label}
                </button>
              );
            })}
          </div>

          {/* Year Filter */}
          <div className="hidden md:flex items-center gap-1 bg-surface-700/50 px-2 py-1 rounded-lg border border-white/5">
            <Calendar size={14} className="text-slate-400 mr-1" />
            <select
              value={yearFilter || ''}
              onChange={e => setYearFilter(e.target.value || null)}
              className="bg-transparent text-[10px] font-mono font-bold text-slate-300 outline-none cursor-pointer"
            >
              <option value="">All Years</option>
              {availableYears.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>

          {/* Risk Heatmap Toggle */}
          <button
            onClick={() => setShowRiskHeatmap(!showRiskHeatmap)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border text-[10px] font-bold uppercase transition-all ${
              showRiskHeatmap
                ? 'bg-red-500/20 text-red-400 border-red-500/30 shadow-[0_0_10px_rgba(239,68,68,0.2)]'
                : 'bg-surface-700/50 text-slate-400 border-white/5 hover:text-slate-300'
            }`}
          >
            <Flame size={14} className={showRiskHeatmap ? 'animate-pulse' : ''} />
            Risk Map
          </button>

          <button onClick={() => loadGraph(focusedNodeId)} className="btn-ghost" disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Graph canvas */}
      <div className="flex-1 relative">
        {nodes.length === 0 && !loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-2xl bg-surface-700 flex items-center justify-center mb-4">
              <FileText size={24} className="text-slate-500" />
            </div>
            <p className="text-slate-400 font-medium">No documents in graph yet</p>
            <p className="text-slate-600 text-sm mt-1">Upload documents to build the knowledge graph</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes.filter((n: any) => {
              if (!yearFilter) return true;
              if (n.data.nodeType !== 'DOCUMENT') return true;
              return n.data.date?.startsWith(yearFilter);
            }).map((n: any) => {
              const isQueryActive = !!activeQuery;
              const isRelevant = isQueryActive && activeQuery?.citations.some(c => c.doc_id === n.id);
              const isRisk = showRiskHeatmap && riskNodes.has(n.id);
              return {
                ...n,
                data: {
                  ...n.data,
                  isHighlighted: n.data.isHighlighted || isRelevant || isRisk,
                  metadata: {
                    ...n.data.metadata,
                    // dim non-relevant nodes if a query is active
                    color: isRisk ? '#ef4444' 
                         : isQueryActive && !isRelevant && n.data.nodeType === 'DOCUMENT' 
                           ? '#475569' 
                           : n.data.metadata?.color
                  }
                }
              };
            })}
            edges={edges.filter((e: any) => !hiddenEdgeTypes.has(e.data?.relation_label))}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodeDoubleClick={(_, node) => setFocusedNodeId(node.id)}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            onPaneClick={() => setSelectedEdge(null)}
            minZoom={0.1}
            maxZoom={2}
            defaultEdgeOptions={{ type: 'smoothstep' }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="#1f2d47"
            />
            <Controls
              className="!bg-surface-700/90 !border-white/10 !rounded-xl !shadow-panel"
            />
            <MiniMap
              nodeColor={(node) => (node.data as { metadata?: { color?: string } })?.metadata?.color || '#4F46E5'}
              nodeStrokeWidth={0}
              className="!bg-surface-800/90 !border-white/10 !rounded-xl"
              maskColor="rgba(8,11,20,0.7)"
            />
          </ReactFlow>
        )}

        {/* Edge detail panel */}
        <EdgePanel />

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface-900/60 backdrop-blur-sm">
            <div className="flex items-center gap-3 text-slate-300">
              <RefreshCw size={20} className="animate-spin text-brand-400" />
              <span className="text-sm">Loading graph...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
