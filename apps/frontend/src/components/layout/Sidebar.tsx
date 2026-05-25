import React, { useEffect, useState } from 'react';
import {
  Upload, GitBranch, Search, FolderOpen,
  Brain, ChevronLeft, ChevronRight, Activity, Bell,
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { api } from '@/api/client';

const NAV_ITEMS = [
  { id: 'ingest',   label: 'Ingest',    icon: Upload,     desc: 'Upload & process' },
  { id: 'graph',    label: 'Graph',     icon: GitBranch,  desc: 'Knowledge map' },
  { id: 'query',    label: 'Query',     icon: Search,     desc: 'Ask anything' },
  { id: 'explorer', label: 'Explorer',  icon: FolderOpen, desc: 'Browse documents' },
  { id: 'alerts',   label: 'Alerts',    icon: Bell,       desc: 'Intelligence alerts' },
] as const;

export function Sidebar() {
  const { activePage, setActivePage, sidebarOpen, setSidebarOpen, stats } = useAppStore();
  const [alertCount, setAlertCount] = useState(0);
  const [criticalCount, setCriticalCount] = useState(0);

  // Fetch alert summary every 30s
  useEffect(() => {
    const fetchAlertSummary = () => {
      api.get<{ unresolved: number; critical_count: number }>('/alerts/summary')
        .then(r => {
          setAlertCount(r.data.unresolved || 0);
          setCriticalCount(r.data.critical_count || 0);
        })
        .catch(() => {});
    };
    fetchAlertSummary();
    const t = setInterval(fetchAlertSummary, 30_000);
    return () => clearInterval(t);
  }, []);

  return (
    <aside
      className={`flex flex-col h-full panel transition-all duration-300 ease-in-out z-20
        ${sidebarOpen ? 'w-56' : 'w-16'}`}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/5">
        <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-violet-600 rounded-lg flex items-center justify-center flex-shrink-0 shadow-glow-brand">
          <Brain size={16} className="text-white" />
        </div>
        {sidebarOpen && (
          <div className="min-w-0 animate-fade-in">
            <p className="text-sm font-bold text-white leading-tight truncate">Cognivault</p>
            <p className="text-[10px] text-slate-500 leading-tight">Knowledge Intelligence</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV_ITEMS.map(({ id, label, icon: Icon, desc }) => {
          const isActive = activePage === id;
          const isAlerts = id === 'alerts';
          const hasBadge = isAlerts && alertCount > 0;
          const isCritical = isAlerts && criticalCount > 0;

          return (
            <button
              key={id}
              id={`nav-${id}`}
              onClick={() => setActivePage(id as any)}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm
                transition-all duration-150 text-left group relative
                ${isActive
                  ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                  : isCritical
                    ? 'text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'}
              `}
            >
              <div className="relative flex-shrink-0">
                <Icon
                  size={18}
                  className={`transition-colors ${
                    isActive ? 'text-brand-400'
                    : isCritical ? 'text-red-400'
                    : 'text-slate-500 group-hover:text-slate-300'
                  }`}
                />
                {/* Badge dot when collapsed */}
                {hasBadge && !sidebarOpen && (
                  <span className={`absolute -top-1 -right-1 w-2 h-2 rounded-full ${isCritical ? 'bg-red-500 animate-pulse' : 'bg-orange-400'}`} />
                )}
              </div>

              {sidebarOpen && (
                <div className="min-w-0 animate-fade-in flex-1 flex items-center justify-between">
                  <div>
                    <p className="font-medium leading-tight">{label}</p>
                    <p className="text-[10px] text-slate-500 leading-tight">{desc}</p>
                  </div>
                  {/* Badge when expanded */}
                  {hasBadge && (
                    <span className={`
                      text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center leading-none
                      ${isCritical ? 'bg-red-500/20 text-red-400 animate-pulse-slow' : 'bg-orange-500/20 text-orange-400'}
                    `}>
                      {alertCount > 99 ? '99+' : alertCount}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* System stats */}
      {sidebarOpen && stats && (
        <div className="mx-2 mb-3 p-3 bg-surface-600/40 rounded-lg border border-white/5 animate-fade-in">
          <div className="flex items-center gap-1.5 mb-2">
            <Activity size={11} className="text-emerald-400" />
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">System</span>
          </div>
          <div className="space-y-1">
            <StatRow label="Documents"  value={stats.total_docs} />
            <StatRow label="Indexed"    value={stats.indexed}    color="text-emerald-400" />
            <StatRow label="Entities"   value={stats.total_entities} />
            <StatRow label="Relations"  value={stats.total_relationships} color="text-violet-400" />
            {alertCount > 0 && (
              <StatRow label="Alerts" value={alertCount} color={criticalCount > 0 ? 'text-red-400' : 'text-orange-400'} />
            )}
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="flex items-center justify-center h-10 border-t border-white/5 text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors"
      >
        {sidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>
    </aside>
  );
}

function StatRow({ label, value, color = 'text-slate-300' }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-[10px] text-slate-500">{label}</span>
      <span className={`text-[11px] font-mono font-semibold ${color}`}>{value.toLocaleString()}</span>
    </div>
  );
}
