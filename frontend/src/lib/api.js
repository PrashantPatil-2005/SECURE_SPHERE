const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  const json = await res.json();
  return json.data ?? json;
}

export const api = {
  getEvents: (limit = 100) => request(`/api/events?limit=${limit}`),
  getIncidents: (limit = 50) => request(`/api/incidents?limit=${limit}`),
  getMetrics: () => request('/api/metrics'),
  getRiskScores: () => request('/api/risk-scores'),
  getTopology: () => request('/topology/graph').catch(() => request('/api/topology/graph')),
  getSystemStatus: () => request('/api/system/status'),
  getMitreMapping: () => request('/api/mitre-mapping'),
  getTopologyChecks: () => request('/api/topology-checks'),
  getDashboardSummary: () => request('/api/dashboard/summary'),
  getTimeline: () => request('/api/metrics/timeline'),
  getDemoStatus: () => request('/api/demo-status'),
  getKillChains: (limit = 20, siteId = '') => request(`/api/kill-chains?limit=${limit}${siteId ? `&site_id=${siteId}` : ''}`),
  getKillChain: (id) => request(`/api/kill-chains/${id}`),
  globalSearch: (query, limit = 50) => request(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`),

  // Raw response (keeps `source` + top-level `data` array) — don't unwrap via request()
  getMttdReport: () =>
    fetch(`${BASE}/api/mttd/report`).then(r => r.json()),

  simulateAttack: (scenario) =>
    fetch(`${BASE}/api/attack/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    }).then(r => r.json()),

  clearEvents: () =>
    fetch(`${BASE}/api/events/clear`, { method: 'POST' }).then(r => r.json()),

  updateIncidentStatus: (id, status, note = '') =>
    fetch(`${BASE}/api/incidents/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, note }),
    }).then(r => r.json()),

  login: (username, password) =>
    fetch(`${BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => r.json()),
};
