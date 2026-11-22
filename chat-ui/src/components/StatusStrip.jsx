import React from 'react';
import { formatClock, toneClass } from '../lib/format';

export default function StatusStrip({ health, lastCommand, backendError, auditBackend }) {
  const tone = health?.tone || 'neutral';
  return (
    <div className="border-b border-slate-800 bg-slate-900/70 px-4 md:px-6 py-2.5 flex flex-nowrap items-center gap-3 text-xs overflow-x-auto">
      <div className="flex items-center gap-2">
        <div className={`score-ring score-${tone}`} style={{ '--p': health?.score ?? 0 }}>
          <span>{health?.score ?? '–'}</span>
        </div>
        <div>
          <div className="font-medium text-slate-100">Namespace health</div>
          <div className={`inline-flex mt-0.5 px-1.5 py-0.5 rounded border font-mono ${toneClass(tone)}`}>
            {health?.grade || 'Waiting'}
          </div>
        </div>
      </div>

      <Stat label="Healthy" value={health?.healthy ?? '–'} />
      <Stat label="Failing" value={health?.failing ?? '–'} warn={health?.failing > 0} />
      <Stat label="Restarts" value={health?.restarts ?? '–'} warn={health?.restarts > 0} />

      {lastCommand?.text ? (
        <div className="min-w-0 basis-full md:basis-auto md:flex-1">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">Last command</div>
          <div className="truncate font-mono text-slate-200">
            {lastCommand.text}
            {lastCommand.status && lastCommand.status !== 'idle' ? (
              <span className="text-slate-500"> · {String(lastCommand.status).replaceAll('_', ' ')}</span>
            ) : null}
            {lastCommand.at ? <span className="text-slate-600"> · {formatClock(lastCommand.at)}</span> : null}
          </div>
        </div>
      ) : <div className="hidden md:block flex-1" />}

      <span className="font-mono text-[10px] uppercase px-2 py-1 rounded border border-slate-700 text-slate-400">
        Audit {auditBackend === 'postgres' ? 'PostgreSQL' : 'memory'}
      </span>

      {backendError ? (
        <span className="px-2 py-1 rounded border border-rose-800 bg-rose-950/50 text-rose-200">{backendError}</span>
      ) : null}
    </div>
  );
}

function Stat({ label, value, warn }) {
  return (
    <div className="px-3 py-1 rounded-lg bg-slate-950 border border-slate-800 shrink-0">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`font-mono text-sm ${warn ? 'text-rose-300' : 'text-slate-100'}`}>{value}</div>
    </div>
  );
}
