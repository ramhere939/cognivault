import React, { useCallback, useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, X, Zap } from 'lucide-react';
import { ingestApi, documentsApi } from '@/api/client';
import { useAppStore } from '@/store/useAppStore';
import type { IngestionJob, ProgressEvent } from '@/types';

const STAGE_LABELS: Record<string, string> = {
  ocr:      'Extracting text (OCR)',
  classify: 'Classifying document',
  chunk:    'Semantic chunking',
  embed:    'Generating embeddings',
  extract:  'Extracting entities',
  graph:    'Building knowledge graph',
  complete: 'Complete',
  error:    'Failed',
};

const STAGE_ORDER = ['ocr', 'classify', 'chunk', 'embed', 'extract', 'graph', 'complete'];

function ProgressBar({ progress, stage }: { progress: number; stage: string }) {
  const isError = stage === 'error';
  const isDone = stage === 'complete';
  return (
    <div className="w-full bg-surface-600 rounded-full h-1.5 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${
          isError ? 'bg-red-500' : isDone ? 'bg-emerald-500' : 'bg-brand-500'
        }`}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

function JobCard({ job }: { job: IngestionJob }) {
  const isComplete = job.stage === 'complete';
  const isError = job.stage === 'error';

  return (
    <div className={`card p-4 animate-slide-in border ${
      isError ? 'border-red-500/30' : isComplete ? 'border-emerald-500/30' : 'border-brand-500/20'
    }`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={16} className="text-slate-400 flex-shrink-0" />
          <span className="text-sm font-medium text-slate-200 truncate">{job.filename}</span>
        </div>
        {isComplete && <CheckCircle size={16} className="text-emerald-400 flex-shrink-0" />}
        {isError && <AlertCircle size={16} className="text-red-400 flex-shrink-0" />}
      </div>

      <ProgressBar progress={job.progress} stage={job.stage} />

      <div className="mt-2 flex items-center gap-2">
        {!isComplete && !isError && (
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
        )}
        <span className="text-xs text-slate-400 truncate">{job.message || STAGE_LABELS[job.stage] || job.stage}</span>
        <span className="ml-auto text-xs font-mono text-slate-500">{job.progress}%</span>
      </div>

      {/* Stage pipeline indicator */}
      <div className="mt-3 flex gap-1">
        {STAGE_ORDER.slice(0, -1).map((s) => {
          const stageIdx = STAGE_ORDER.indexOf(s);
          const currentIdx = STAGE_ORDER.indexOf(job.stage);
          const isPast = currentIdx > stageIdx;
          const isCurrent = s === job.stage;
          return (
            <div
              key={s}
              className={`flex-1 h-0.5 rounded transition-all duration-300 ${
                isError ? 'bg-red-500/30' :
                isPast || isComplete ? 'bg-emerald-500' :
                isCurrent ? 'bg-brand-400 animate-pulse' :
                'bg-surface-500'
              }`}
            />
          );
        })}
      </div>
    </div>
  );
}

export function IngestPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { ingestionJobs, upsertJob, removeJob, upsertDocument, setStats } = useAppStore();

  const startIngestion = useCallback(async (files: File[]) => {
    setIsUploading(true);
    for (const file of files) {
      try {
        const response = await ingestApi.upload(file);
        const { doc_id, filename } = response;

        // Init job state
        upsertJob({ doc_id, filename, stage: 'ocr', progress: 0, message: 'Starting...' });

        // Connect SSE stream
        const baseUrl = import.meta.env.VITE_API_URL || '/api';
        const eventSource = new EventSource(`${baseUrl}/ingest/${doc_id}/stream`);

        eventSource.onmessage = (event) => {
          try {
            const data: ProgressEvent = JSON.parse(event.data);
            if (data.stage === 'done' || data.stage === 'ping') return;

            upsertJob({
              doc_id: data.doc_id || doc_id,
              filename,
              stage: data.stage,
              progress: data.progress,
              message: data.message,
              error: data.error,
            });

            if (data.stage === 'complete' || data.stage === 'error') {
              eventSource.close();
              // Refresh document list and stats
              setTimeout(() => {
                documentsApi.list().then(docs => useAppStore.getState().setDocuments(docs));
                documentsApi.stats().then(useAppStore.getState().setStats);
              }, 1000);
            }
          } catch {
            // ignore parse errors
          }
        };

        eventSource.onerror = () => {
          eventSource.close();
          upsertJob({ doc_id, filename, stage: 'error', progress: 0, message: 'Connection lost' });
        };

      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Upload failed';
        console.error(`Failed to upload ${file.name}:`, err);
      }
    }
    setIsUploading(false);
  }, [upsertJob]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f =>
      f.type === 'application/pdf' || f.name.endsWith('.txt') || f.name.endsWith('.md')
    );
    if (files.length) startIngestion(files);
  }, [startIngestion]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length) startIngestion(files);
    e.target.value = '';
  }, [startIngestion]);

  const activeJobs = Object.values(ingestionJobs);

  return (
    <div className="h-full p-6 overflow-y-auto">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Document Ingestion</h1>
          <p className="text-slate-400 text-sm mt-1">
            Upload PDFs, policy documents, contracts, circulars — the AI pipeline handles the rest.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onClick={() => fileInputRef.current?.click()}
          className={`
            relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
            transition-all duration-200 group
            ${isDragging
              ? 'border-brand-400 bg-brand-500/10 scale-[1.01]'
              : 'border-white/10 hover:border-brand-500/50 hover:bg-white/2'
            }
          `}
        >
          {/* Background grid */}
          <div className="absolute inset-0 bg-grid-pattern rounded-2xl opacity-50 pointer-events-none" />

          <div className="relative">
            <div className={`
              mx-auto w-16 h-16 rounded-2xl flex items-center justify-center mb-4
              transition-all duration-200 shadow-glow-brand
              ${isDragging ? 'bg-brand-500/30 scale-110' : 'bg-brand-600/20 group-hover:bg-brand-500/20'}
            `}>
              <Upload size={28} className={`transition-colors ${isDragging ? 'text-brand-300' : 'text-brand-400'}`} />
            </div>

            <p className="text-lg font-semibold text-slate-200 mb-1">
              {isDragging ? 'Drop to ingest' : 'Drop documents here'}
            </p>
            <p className="text-sm text-slate-500 mb-4">
              or <span className="text-brand-400 underline underline-offset-2">browse files</span>
            </p>

            <div className="flex items-center justify-center gap-2 flex-wrap">
              {['PDF', 'TXT', 'MD'].map(ext => (
                <span key={ext} className="px-2 py-0.5 bg-surface-600 rounded text-xs text-slate-400 font-mono">
                  .{ext.toLowerCase()}
                </span>
              ))}
              <span className="text-xs text-slate-600">· Max 50MB</span>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.md"
            onChange={handleFileInput}
            className="hidden"
          />
        </div>

        {/* Pipeline explanation */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={14} className="text-brand-400" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI Pipeline</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {['OCR / Parse', 'Classify', 'Chunk', 'Embed', 'Extract Entities', 'Build Graph'].map((step, i, arr) => (
              <React.Fragment key={step}>
                <span className="text-xs text-slate-400 bg-surface-600 px-2 py-1 rounded">{step}</span>
                {i < arr.length - 1 && <span className="text-slate-600 text-xs">→</span>}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Active jobs */}
        {activeJobs.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-300">
                Processing ({activeJobs.length})
              </h2>
              <button
                onClick={() => activeJobs.filter(j => j.stage === 'complete' || j.stage === 'error')
                  .forEach(j => removeJob(j.doc_id))}
                className="btn-ghost text-xs"
              >
                <X size={12} /> Clear done
              </button>
            </div>
            {activeJobs.map(job => (
              <JobCard key={job.doc_id} job={job} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
