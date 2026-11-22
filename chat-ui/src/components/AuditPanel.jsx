import React from 'react';
import { formatClock } from '../lib/format';

export default function AuditPanel({ auditLogs, backend }) {
  return (
    <section className="flex-1 overflow-y-auto p-4 md:p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-end justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-50">Audit history</h2>
            <p className="text-sm text-slate-400">Prompts, approvals, and demo actions. Stored in {backend === 'postgres' ? 'PostgreSQL' : 'memory until Postgres is reachable'}.</p>
          </div>
          <span className="text-xs font-mono text-slate-500">{auditLogs.length} events</span>
        </div>

        {auditLogs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center text-sm text-slate-500">
            No audit events yet. Ask the assistant something or run a demo scenario.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-800">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-900 text-[11px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Time</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Target</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Detail</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} className="border-t border-slate-800 bg-slate-950/40">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">{formatClock(log.timestamp)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-cyan-200">{log.action}</td>
                    <td className="px-4 py-3 text-slate-200">{log.target}</td>
                    <td className="px-4 py-3">
                      <StatusPill status={log.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate">
                      {log.details?.summary || log.details?.query || log.details?.scenario || log.user}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

function StatusPill({ status }) {
  const text = String(status || '').replaceAll('_', ' ');
  const ok = /EXECUTED|APPROVED/.test(status || '');
  const bad = /REJECT|FAIL|EXPIRED/.test(status || '');
  const tone = ok ? 'text-emerald-200 border-emerald-800 bg-emerald-950/40' : bad ? 'text-rose-200 border-rose-800 bg-rose-950/40' : 'text-amber-100 border-amber-800 bg-amber-950/40';
  return <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${tone}`}>{text}</span>;
}
