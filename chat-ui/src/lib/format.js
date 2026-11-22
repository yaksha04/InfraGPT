export function healthFromPods(pods) {
  const list = Array.isArray(pods) ? pods : [];
  const total = list.length;
  const healthy = list.filter((pod) => pod.is_healthy).length;
  const restarts = list.reduce((sum, pod) => sum + (Number(pod.restarts) || 0), 0);
  const score = total === 0 ? 100 : Math.max(0, Math.round((healthy / total) * 100) - Math.min(25, restarts));
  let grade = 'No workloads';
  let tone = 'neutral';
  if (total > 0 && score >= 90) {
    grade = 'Healthy';
    tone = 'good';
  } else if (total > 0 && score >= 60) {
    grade = 'Degraded';
    tone = 'warn';
  } else if (total > 0) {
    grade = 'Critical';
    tone = 'bad';
  }
  return {
    score,
    grade,
    tone,
    healthy,
    failing: total - healthy,
    restarts,
    total,
  };
}

export function memoryTone(limit) {
  if (!limit) return 'neutral';
  const text = String(limit).toLowerCase();
  const amount = parseInt(text, 10);
  if (Number.isNaN(amount)) return 'neutral';
  if (text.includes('gi')) return amount >= 1 ? 'good' : 'warn';
  if (amount <= 128) return 'bad';
  if (amount <= 256) return 'warn';
  return 'good';
}

export function toneClass(tone) {
  if (tone === 'good') return 'text-emerald-300 bg-emerald-950/50 border-emerald-800/70';
  if (tone === 'warn') return 'text-amber-200 bg-amber-950/40 border-amber-800/70';
  if (tone === 'bad') return 'text-rose-200 bg-rose-950/50 border-rose-800/80';
  return 'text-slate-300 bg-slate-900 border-slate-700';
}

export function parseAnalysis(text) {
  if (!text || !text.includes('**Root Cause**')) return null;
  const labels = ['Root Cause', 'Evidence', 'Suggested Fix', 'Risk Level'];
  const found = {};
  for (const label of labels) {
    const match = text.match(new RegExp(`\\*\\*${label}\\*\\*\\s*([\\s\\S]*?)(?=\\n\\*\\*|$)`));
    if (!match) return null;
    found[label] = match[1].trim();
  }
  const risk = found['Risk Level'].split('\n')[0].trim();
  found.riskTone = /high/i.test(risk) ? 'bad' : /medium/i.test(risk) ? 'warn' : 'good';
  return found;
}

export function formatClock(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export const SRE_COMMANDS = [
  { label: 'Why is payment failing?', prompt: 'Why is payment-service failing?' },
  { label: 'Highest restarts', prompt: 'Show pods with highest restarts' },
  { label: 'Restart frontend', prompt: 'Restart frontend safely' },
  { label: 'Scale auth to 4', prompt: 'Scale auth service to 4' },
  { label: 'CrashLoop logs', prompt: 'Show logs of CrashLoop pods' },
  { label: 'Explain OOMKilled', prompt: 'Explain this OOMKilled error' },
];
