import React from 'react';
import { formatClock, toneClass } from '../lib/format';

export default function ApprovalModal({ pendingApproval, onConfirm, onCancel, isProcessing, error }) {
  if (!pendingApproval) return null;
  const { tool_name, args, approval_id, summary, before, after, risk, expires_at } = pendingApproval;
  const riskTone = /high/i.test(risk || '') ? 'bad' : /low/i.test(risk || '') ? 'good' : 'warn';

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-amber-900/60 bg-amber-950/40">
          <div className="text-xs uppercase tracking-wide text-amber-200/80">Approval required</div>
          <h3 className="text-base font-semibold text-amber-50 mt-1">{summary || tool_name}</h3>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px] font-mono">
            <span className={`px-2 py-0.5 rounded border ${toneClass(riskTone)}`}>Risk {risk || 'Medium'}</span>
            <span className="px-2 py-0.5 rounded border border-slate-700 text-slate-300">{tool_name}</span>
            {expires_at ? <span className="px-2 py-0.5 rounded border border-slate-700 text-slate-400">Expires {formatClock(expires_at)}</span> : null}
          </div>
        </div>

        <div className="p-5 grid md:grid-cols-2 gap-3">
          <Diff title="Before" data={before} />
          <Diff title="After" data={after} />
        </div>

        <div className="px-5 pb-4 text-xs text-slate-400">
          Target <span className="font-mono text-slate-200">{args?.name || args?.pod_name || args?.deployment_name || 'cluster'}</span>
          {' '}in <span className="font-mono text-slate-200">{args?.namespace || 'default'}</span>.
          Nothing is changed until you approve.
        </div>

        {error ? (
          <div className="mx-5 mb-4 rounded-xl border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-100">{error}</div>
        ) : null}

        <div className="px-5 py-4 border-t border-slate-800 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => onCancel(approval_id)}
            disabled={isProcessing}
            className="px-4 py-2 rounded-xl border border-slate-700 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            Reject
          </button>
          <button
            type="button"
            onClick={() => onConfirm(approval_id)}
            disabled={isProcessing}
            className="px-4 py-2 rounded-xl bg-emerald-400 text-slate-950 text-sm font-semibold disabled:opacity-50"
          >
            {isProcessing ? 'Applying…' : 'Approve and apply'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Diff({ title, data }) {
  const entries = Object.entries(data || {});
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
      <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">{title}</div>
      {entries.length === 0 ? (
        <div className="text-xs text-slate-500">No values</div>
      ) : (
        <dl className="space-y-1.5">
          {entries.map(([key, value]) => (
            <div key={key} className="flex justify-between gap-3 text-xs">
              <dt className="text-slate-500">{key}</dt>
              <dd className="font-mono text-slate-100 text-right break-all">{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function formatValue(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
