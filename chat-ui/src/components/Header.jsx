import React from 'react';

const VIEWS = [
  { id: 'operate', label: 'Assistant' },
  { id: 'scenarios', label: 'Scenarios' },
  { id: 'audit', label: 'Audit' },
];

export default function Header({
  clusterStatus,
  activeNamespace,
  onNamespaceChange,
  onRefresh,
  isRefreshing,
  view,
  onViewChange,
}) {
  const isLive = clusterStatus?.mode === 'live';
  const namespaces = clusterStatus?.namespaces?.length
    ? clusterStatus.namespaces
    : ['production', 'default', 'staging'];

  return (
    <header className="border-b border-slate-800 bg-slate-950/90 backdrop-blur px-4 md:px-6 py-3 flex flex-wrap items-center gap-3 justify-between shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-10 h-10 rounded-xl bg-cyan-400 text-slate-950 flex items-center justify-center font-mono font-bold shadow-[0_0_24px_rgba(34,211,238,0.25)]">
          IG
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="font-semibold tracking-tight text-slate-50">InfraGPT</h1>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
              SRE
            </span>
          </div>
          <p className="text-xs text-slate-400 truncate">Natural language Kubernetes, with a human approval gate</p>
        </div>
      </div>

      <nav className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
        {VIEWS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onViewChange(item.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              view === item.id ? 'bg-slate-100 text-slate-950' : 'text-slate-400 hover:text-slate-100'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono">
          <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400' : 'bg-amber-300'}`} />
          <span className="text-slate-200">{isLive ? 'Live cluster' : 'Simulator'}</span>
          <span className="text-slate-600">/</span>
          <span className="text-cyan-300">{clusterStatus?.ai_engine || 'SRE engine'}</span>
        </div>

        <label className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5">
          <span className="text-[11px] uppercase tracking-wide text-slate-500">Namespace</span>
          <select
            aria-label="Namespace"
            value={namespaces.includes(activeNamespace) ? activeNamespace : namespaces[0]}
            onChange={(event) => onNamespaceChange(event.target.value)}
            className="bg-transparent text-xs font-mono text-cyan-300 focus:outline-none cursor-pointer min-w-[6.5rem]"
          >
            {namespaces.map((namespace) => (
              <option key={namespace} value={namespace} className="bg-slate-900 text-slate-100">
                {namespace}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh cluster"
          className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 disabled:opacity-50"
        >
          <svg className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </header>
  );
}
