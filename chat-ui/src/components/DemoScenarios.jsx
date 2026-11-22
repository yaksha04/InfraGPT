import React, { useState } from 'react';

const SCENARIOS = [
  {
    id: 'oom',
    title: 'Trigger OOM',
    eyebrow: 'payment-service',
    detail: 'Drops the memory limit to 128Mi and puts the payment pod into CrashLoopBackOff with exit code 137.',
    followup: 'Why is payment-service failing?',
    tone: 'border-rose-900 bg-rose-950/20',
  },
  {
    id: 'crashloop',
    title: 'Trigger CrashLoop',
    eyebrow: 'order-service',
    detail: 'Removes REDIS_HOST so order-service exits on boot and the kubelet keeps restarting it.',
    followup: 'Why is order-service failing?',
    tone: 'border-amber-900 bg-amber-950/20',
  },
  {
    id: 'restore',
    title: 'Restore Healthy State',
    eyebrow: 'whole namespace',
    detail: 'Returns the simulator workloads to running replicas, safe memory limits, and the config they need.',
    followup: 'Show pods with highest restarts',
    tone: 'border-emerald-900 bg-emerald-950/20',
  },
];

export default function DemoScenarios({ activeNamespace, onRun, onAsk, isBusy, notice }) {
  const [pending, setPending] = useState(null);

  const run = async (scenario) => {
    setPending(scenario.id);
    try {
      await onRun(scenario);
    } finally {
      setPending(null);
    }
  };

  return (
    <section className="flex-1 overflow-y-auto p-4 md:p-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-lg font-semibold text-slate-50">Demo scenarios</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-2xl">
          One click changes the simulator in <span className="font-mono text-cyan-200">{activeNamespace}</span>.
          These buttons do not touch a live cluster. After a failure, ask the assistant for the root cause.
        </p>

        {notice ? (
          <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${notice.ok ? 'border-emerald-800 bg-emerald-950/30 text-emerald-50' : 'border-rose-800 bg-rose-950/40 text-rose-50'}`}>
            <div className="font-medium">{notice.title}</div>
            <div className="text-xs mt-1 opacity-80">{notice.detail}</div>
          </div>
        ) : null}

        <div className="grid md:grid-cols-3 gap-4 mt-5">
          {SCENARIOS.map((scenario) => (
            <article key={scenario.id} className={`rounded-2xl border p-4 flex flex-col ${scenario.tone}`}>
              <div className="text-[11px] uppercase tracking-wide text-slate-400">{scenario.eyebrow}</div>
              <h3 className="text-base font-semibold text-slate-50 mt-1">{scenario.title}</h3>
              <p className="text-sm text-slate-300 mt-2 flex-1">{scenario.detail}</p>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => run(scenario)}
                className="mt-4 px-3 py-2 rounded-xl bg-slate-100 text-slate-950 text-sm font-semibold disabled:opacity-40"
              >
                {pending === scenario.id ? 'Applying…' : scenario.title}
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => onAsk(scenario.followup)}
                className="mt-2 text-xs text-cyan-200 text-left hover:text-cyan-100"
              >
                Then ask: {scenario.followup}
              </button>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
