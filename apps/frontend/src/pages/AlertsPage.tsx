import { useState, useEffect } from 'react'
import { Bell, AlertTriangle, AlertCircle, Info, CheckCircle2, RefreshCw, Shield, XCircle, ArrowRight } from 'lucide-react'
import { api } from '../api/client'

interface Alert {
  id: string
  alert_type: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  title: string
  explanation: string
  reasoning_trace: string | null
  affected_doc_ids: string[]
  evidence_chunks: Array<{
    chunk_id: string
    doc_id: string
    doc_title: string | null
    quote: string
    page_num: number | null
  }>
  confidence: number
  operational_risk: string | null
  resolved: boolean
  created_at: string
  graph_edge_id: string | null
}

interface AlertSummary {
  total: number
  unresolved: number
  critical_count: number
  by_severity: Record<string, number>
  by_type: Record<string, number>
}

const SEVERITY_CONFIG = {
  CRITICAL: { color: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/40',  ring: 'ring-red-500/60', icon: XCircle,        pulse: true  },
  HIGH:     { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/40',ring: 'ring-orange-500/40', icon: AlertTriangle, pulse: false },
  MEDIUM:   { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/40',ring: 'ring-yellow-500/40', icon: AlertCircle,  pulse: false },
  LOW:      { color: 'text-blue-400',   bg: 'bg-blue-500/10',   border: 'border-blue-500/40',  ring: 'ring-blue-500/40',  icon: Info,         pulse: false },
  INFO:     { color: 'text-slate-400',  bg: 'bg-slate-500/10',  border: 'border-slate-500/40', ring: 'ring-slate-500/40', icon: Info,         pulse: false },
}

const TYPE_LABELS: Record<string, string> = {
  SUPERSESSION:        'Supersession',
  POLICY_CONFLICT:     'Policy Conflict',
  MISSING_APPROVAL:    'Missing Approval',
  DUPLICATE_INVOICE:   'Duplicate Invoice',
  VENDOR_RISK:         'Vendor Risk',
  COMPLIANCE_GAP:      'Compliance Gap',
  TIMELINE_ANOMALY:    'Timeline Anomaly',
  ORPHANED_REFERENCE:  'Orphaned Reference',
  OPERATIONAL_BLOCK:   'Operational Block',
  CIRCULAR_DEPENDENCY: 'Circular Dependency',
}

export default function AlertsPage() {
  const [alerts, setAlerts]         = useState<Alert[]>([])
  const [summary, setSummary]       = useState<AlertSummary | null>(null)
  const [loading, setLoading]       = useState(true)
  const [expanded, setExpanded]     = useState<string | null>(null)
  const [filterSev, setFilterSev]   = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string | null>(null)
  const [resolving, setResolving]   = useState<string | null>(null)

  const fetchAlerts = async () => {
    setLoading(true)
    try {
      const [alertsRes, summaryRes] = await Promise.all([
        api.get<{ alerts: Alert[]; total: number }>('/alerts', {
          params: { resolved: false, page_size: 50 }
        }),
        api.get<AlertSummary>('/alerts/summary'),
      ])
      setAlerts(alertsRes.data.alerts)
      setSummary(summaryRes.data)
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAlerts() }, [])

  const handleResolve = async (id: string) => {
    setResolving(id)
    try {
      await api.patch(`/alerts/${id}/resolve`)
      setAlerts(prev => prev.filter(a => a.id !== id))
      if (summary) {
        setSummary({ ...summary, unresolved: summary.unresolved - 1 })
      }
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    } finally {
      setResolving(null)
    }
  }

  const filtered = alerts.filter(a =>
    (!filterSev  || a.severity   === filterSev)  &&
    (!filterType || a.alert_type === filterType)
  )

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
              <Bell className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Intelligence Alerts</h1>
              <p className="text-xs text-slate-400">
                Proactive risk detection — citation-backed findings
              </p>
            </div>
          </div>
          <button onClick={fetchAlerts} className="btn-ghost" disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Summary strip */}
        {summary && (
          <div className="mt-4 grid grid-cols-4 gap-3">
            <SummaryCard
              label="Unresolved"
              value={summary.unresolved}
              color="text-white"
              bg="bg-surface-600/60"
            />
            <SummaryCard
              label="Critical"
              value={summary.critical_count}
              color="text-red-400"
              bg="bg-red-500/10 border border-red-500/20"
              pulse={summary.critical_count > 0}
            />
            <SummaryCard
              label="High"
              value={summary.by_severity?.HIGH || 0}
              color="text-orange-400"
              bg="bg-orange-500/10 border border-orange-500/20"
            />
            <SummaryCard
              label="Total Detected"
              value={summary.total}
              color="text-slate-300"
              bg="bg-surface-600/60"
            />
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex-shrink-0 px-6 py-2 border-b border-white/5 flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-500">Filter:</span>
        {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
          <button
            key={sev}
            onClick={() => setFilterSev(filterSev === sev ? null : sev)}
            className={`px-2 py-0.5 rounded text-xs font-medium transition-all ${
              filterSev === sev
                ? `${SEVERITY_CONFIG[sev as keyof typeof SEVERITY_CONFIG].bg} ${SEVERITY_CONFIG[sev as keyof typeof SEVERITY_CONFIG].color} ring-1 ${SEVERITY_CONFIG[sev as keyof typeof SEVERITY_CONFIG].ring}`
                : 'bg-surface-600/40 text-slate-400 hover:text-white'
            }`}
          >
            {sev}
          </button>
        ))}
        <div className="w-px h-4 bg-white/10 mx-1" />
        {Object.entries(TYPE_LABELS).map(([type, label]) => (
          <button
            key={type}
            onClick={() => setFilterType(filterType === type ? null : type)}
            className={`px-2 py-0.5 rounded text-xs font-medium transition-all ${
              filterType === type
                ? 'bg-brand-600/30 text-brand-300 ring-1 ring-brand-500/40'
                : 'bg-surface-600/40 text-slate-500 hover:text-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
        {(filterSev || filterType) && (
          <button
            onClick={() => { setFilterSev(null); setFilterType(null) }}
            className="text-xs text-slate-500 hover:text-white ml-2"
          >
            Clear
          </button>
        )}
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <RefreshCw className="w-6 h-6 text-brand-400 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState hasFilters={!!(filterSev || filterType)} />
        ) : (
          filtered.map(alert => (
            <AlertCard
              key={alert.id}
              alert={alert}
              expanded={expanded === alert.id}
              onToggle={() => setExpanded(expanded === alert.id ? null : alert.id)}
              onResolve={() => handleResolve(alert.id)}
              resolving={resolving === alert.id}
            />
          ))
        )}
      </div>
    </div>
  )
}

function SummaryCard({
  label, value, color, bg, pulse = false
}: { label: string; value: number; color: string; bg: string; pulse?: boolean }) {
  return (
    <div className={`card p-3 ${pulse && value > 0 ? 'animate-glow' : ''}`}>
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  )
}

function AlertCard({
  alert, expanded, onToggle, onResolve, resolving
}: {
  alert: Alert
  expanded: boolean
  onToggle: () => void
  onResolve: () => void
  resolving: boolean
}) {
  const cfg = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.INFO
  const Icon = cfg.icon

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} transition-all duration-200`}>
      {/* Main row */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer"
        onClick={onToggle}
      >
        <div className={`mt-0.5 flex-shrink-0 ${cfg.pulse && !alert.resolved ? 'animate-pulse-slow' : ''}`}>
          <Icon className={`w-5 h-5 ${cfg.color}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.color} ring-1 ${cfg.ring}`}>
              {alert.severity}
            </span>
            <span className="text-xs text-slate-500 bg-surface-600/50 px-2 py-0.5 rounded-full">
              {TYPE_LABELS[alert.alert_type] || alert.alert_type}
            </span>
            <span className="text-xs text-slate-600">
              {Math.round(alert.confidence * 100)}% confidence
            </span>
          </div>
          <h3 className="text-sm font-semibold text-white mt-1.5">{alert.title}</h3>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">{alert.explanation}</p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <button
            onClick={e => { e.stopPropagation(); onResolve() }}
            disabled={resolving}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-green-400 transition-colors px-2 py-1 rounded hover:bg-green-500/10"
            title="Mark as resolved"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            {resolving ? 'Resolving…' : 'Resolve'}
          </button>
          <ArrowRight className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`} />
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/5 mt-1 pt-3 space-y-3 animate-fade-in">
          {/* Operational Risk */}
          {alert.operational_risk && (
            <div className="flex items-start gap-2 bg-surface-700/50 rounded-lg p-3">
              <Shield className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-xs font-medium text-orange-400 mb-0.5">Operational Risk</div>
                <div className="text-xs text-slate-300">{alert.operational_risk}</div>
              </div>
            </div>
          )}

          {/* Reasoning Trace */}
          {alert.reasoning_trace && (
            <div>
              <div className="text-xs font-medium text-slate-500 mb-1">Reasoning Trace</div>
              <div className="text-xs text-slate-400 font-mono bg-surface-800 rounded p-2 leading-relaxed">
                {alert.reasoning_trace}
              </div>
            </div>
          )}

          {/* Evidence */}
          {alert.evidence_chunks.length > 0 && (
            <div>
              <div className="text-xs font-medium text-slate-500 mb-2">Evidence</div>
              <div className="space-y-2">
                {alert.evidence_chunks.map((chunk, i) => (
                  <div key={i} className="bg-surface-800/60 rounded-lg p-3 border border-white/5">
                    <div className="text-xs font-medium text-brand-400 mb-1">
                      {chunk.doc_title || chunk.doc_id}
                      {chunk.page_num && <span className="text-slate-500 ml-2">p.{chunk.page_num}</span>}
                    </div>
                    <blockquote className="text-xs text-slate-300 italic border-l-2 border-brand-500/40 pl-2">
                      "{chunk.quote}"
                    </blockquote>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Affected docs */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500">Affected:</span>
            {alert.affected_doc_ids.map(id => (
              <span key={id} className="text-xs text-slate-400 bg-surface-700/50 px-2 py-0.5 rounded font-mono">
                {id.slice(0, 8)}…
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <div className="p-4 rounded-full bg-green-500/10 border border-green-500/20 mb-4">
        <Shield className="w-8 h-8 text-green-400" />
      </div>
      <h3 className="text-base font-semibold text-white">
        {hasFilters ? 'No alerts match your filters' : 'No active alerts'}
      </h3>
      <p className="text-sm text-slate-500 mt-1 max-w-xs">
        {hasFilters
          ? 'Try clearing your filters to see all alerts.'
          : 'The intelligence engine has not detected any policy conflicts, risks, or compliance gaps.'}
      </p>
    </div>
  )
}
