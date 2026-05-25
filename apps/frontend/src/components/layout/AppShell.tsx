import React, { useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { IngestPage } from '@/pages/IngestPage';
import { GraphPage } from '@/pages/GraphPage';
import { QueryPage } from '@/pages/QueryPage';
import { ExplorerPage } from '@/pages/ExplorerPage';
import AlertsPage from '@/pages/AlertsPage';
import { useAppStore } from '@/store/useAppStore';
import { documentsApi } from '@/api/client';

export function AppShell() {
  const { activePage, setDocuments, setStats } = useAppStore();

  // Load initial data
  useEffect(() => {
    documentsApi.list().then(setDocuments).catch(console.error);
    documentsApi.stats().then(setStats).catch(console.error);

    // Refresh stats every 60s (reduced from 30s)
    const interval = setInterval(() => {
      documentsApi.stats().then(setStats).catch(console.error);
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <main className="flex-1 overflow-hidden relative">
        {/* Ambient background gradient */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-600/5 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-violet-600/5 rounded-full blur-3xl" />
        </div>

        <div className="relative h-full overflow-auto">
          {activePage === 'ingest'   && <IngestPage />}
          {activePage === 'graph'    && <GraphPage />}
          {activePage === 'query'    && <QueryPage />}
          {activePage === 'explorer' && <ExplorerPage />}
          {activePage === 'alerts'   && <AlertsPage />}
        </div>
      </main>
    </div>
  );
}
