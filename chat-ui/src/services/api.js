import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE || '';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function apiErrorMessage(err) {
  const data = err?.response?.data;
  if (data?.error && data?.message && data.message !== data.error) {
    return `**${data.error}**\n\n${data.message}`;
  }
  if (typeof data?.error === 'string') {
    return `**${data.error}**`;
  }
  if (typeof data?.detail === 'string') {
    return `**${data.detail}**`;
  }
  if (err?.code === 'ECONNABORTED') {
    return '**Kubernetes unavailable**\n\nThe request timed out before the cluster answered.';
  }
  return '**InfraGPT backend unreachable**\n\nThe dashboard could not reach the orchestrator. Start it on port 8888 and refresh.';
}

export const api = {
  getClusterStatus: async () => {
    const res = await client.get('/api/cluster/status');
    return res.data;
  },

  getPods: async (namespace = 'production') => {
    const res = await client.get(`/api/cluster/pods?namespace=${encodeURIComponent(namespace)}`);
    return res.data.pods || [];
  },

  getDeployments: async (namespace = 'production') => {
    const res = await client.get(`/api/cluster/deployments?namespace=${encodeURIComponent(namespace)}`);
    return res.data.deployments || [];
  },

  getNodes: async () => {
    const res = await client.get('/api/cluster/nodes');
    return res.data.nodes || [];
  },

  getHealth: async (namespace = 'production') => {
    const res = await client.get(`/api/cluster/health?namespace=${encodeURIComponent(namespace)}`);
    return res.data;
  },

  getAuditLogs: async () => {
    const res = await client.get('/api/audit/logs');
    return res.data;
  },

  getScenarios: async () => {
    const res = await client.get('/api/demo/scenarios');
    return res.data.scenarios || [];
  },

  runDemo: async (scenario, namespace = 'production') => {
    const res = await client.post('/api/demo/scenario', { scenario, namespace });
    return res.data;
  },

  sendMessage: async (message, namespace = 'production', history = []) => {
    const res = await client.post('/api/chat', {
      message,
      namespace,
      session_id: 'web-session',
      history,
    });
    return res.data;
  },

  approveAction: async (approvalId, approved) => {
    const res = await client.post('/api/chat/approve', {
      approval_id: approvalId,
      approved,
    });
    return res.data;
  },
};
