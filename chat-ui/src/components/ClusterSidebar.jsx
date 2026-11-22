import React, { useState } from 'react';
import { healthFromPods, memoryTone, toneClass } from '../lib/format';

export default function ClusterSidebar({ pods, deployments, activeNamespace, onSelectPodForLog, onAsk }) {
  const [activeTab, setActiveTab] = useState('pods');
  const health = healthFromPods(pods);

  return (
    <aside className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-slate-800 bg-slate-950/60 flex flex-col shrink-0 h-full min-h-0 overflow-hidden">
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Cluster</span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 text-cyan-300 border border-slate-800">
            {activeNamespace}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Metric label="Score" value={health.score} tone={health.tone} />
          <Metric label="Failing" value={health.failing} tone={health.failing ? 'bad' : 'good'} />
          <Metric label="Restarts" value={health.restarts} tone={health.restarts ? 'warn' : 'good'} />
        </div>
      </div>

      <div className="flex border-b border-slate-800 bg-slate-950 p-1">
        <TabButton active={activeTab === 'pods'} onClick={() => setActiveTab('pods')}>
          Pods ({pods.length})
        </TabButton>
        <TabButton active={activeTab === 'deployments'} onClick={() => setActiveTab('deployments')}>
          Deploy ({deployments.length})
        </TabButton>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {activeTab === 'pods' ? (
          pods.length === 0 ? (
            <Empty>No pods in {activeNamespace}</Empty>
          ) : (
            pods.map((pod) => {
              const restarts = Number(pod.restarts) || 0;
              return (
                <button
                  type="button"
                  key={pod.name}
                  onClick={() => onSelectPodForLog && onSelectPodForLog(pod.name)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                    pod.is_healthy
                      ? 'bg-slate-950 border-slate-800 hover:border-slate-600'
                      : 'bg-rose-950/20 border-rose-900 hover:border-rose-700'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="font-mono text-xs text-slate-100 truncate" title={pod.name}>{pod.name}</div>
                    <div className="text-[10px] text-slate-500 mt-1">{pod.node || 'unassigned'}</div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border whitespace-nowrap ${toneClass(pod.is_healthy ? 'good' : 'bad')}`}>
                      {pod.status}
                    </span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${toneClass(restarts >= 3 ? 'bad' : restarts > 0 ? 'warn' : 'good')}`}>
                      {restarts} {restarts === 1 ? 'restart' : 'restarts'}
                    </span>
                    <span
                      className="text-[10px] text-cyan-300 hover:text-cyan-200"
                      onClick={(event) => {
                        event.stopPropagation();
                        onAsk && onAsk(`Why is pod ${pod.name} failing?`);
                      }}
                    >
                      Diagnose
                    </span>
                  </div>
                </button>
              );
            })
          )
        ) : deployments.length === 0 ? (
          <Empty>No deployments in {activeNamespace}</Empty>
        ) : (
          deployments.map((dep) => {
            const desired = dep.desired_replicas ?? dep.replicas ?? 0;
            const available = dep.available_replicas ?? 0;
            const replicaTone = available < desired ? 'bad' : 'good';
            return (
              <div key={dep.name} className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-slate-100 truncate">{dep.name}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${toneClass(replicaTone)}`}>
                    {available}/{desired}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-500 truncate">{dep.image || (dep.images || []).join(', ') || 'image unknown'}</div>
                <div className="flex gap-1.5 flex-wrap">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${toneClass(memoryTone(dep.memory_limit))}`}>
                    mem {dep.memory_limit || 'default'}
                  </span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${toneClass(cpuTone(dep.cpu_limit))}`}>
                    cpu {dep.cpu_limit || 'default'}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}

function cpuTone(limit) {
  if (!limit) return 'neutral';
  const text = String(limit).toLowerCase();
  const amount = parseInt(text, 10);
  if (Number.isNaN(amount)) return 'neutral';
  if (text.endsWith('m')) return amount < 150 ? 'warn' : 'good';
  return amount < 1 ? 'warn' : 'good';
}

function Metric({ label, value, tone }) {
  return (
    <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
      <div className="text-[10px] uppercase font-mono text-slate-500">{label}</div>
      <div className={`text-lg font-mono font-semibold ${tone === 'bad' ? 'text-rose-300' : tone === 'warn' ? 'text-amber-200' : 'text-emerald-300'}`}>
        {value}
      </div>
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 py-1.5 text-xs font-medium rounded-md ${active ? 'bg-slate-800 text-slate-50' : 'text-slate-400'}`}
    >
      {children}
    </button>
  );
}

function Empty({ children }) {
  return <div className="text-center py-8 text-xs text-slate-500 font-mono">{children}</div>;
}
