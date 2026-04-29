const BASE = import.meta.env.VITE_API_URL ?? '';

function authToken() {
  try {
    return (
      localStorage.getItem('securisphere_token') ||
      sessionStorage.getItem('securisphere_token') ||
      ''
    );
  } catch {
    return '';
  }
}

// Wrapped fetch — auto-injects Authorization: Bearer <token> on every call.
// Use this everywhere instead of raw fetch so backend `token_required`
// endpoints don't 401.
function authFetch(input, init = {}) {
  const t = authToken();
  const headers = new Headers(init.headers || {});
  if (t && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${t}`);
  return fetch(input, { ...init, headers });
}

async function request(path) {
  const res = await authFetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  const json = await res.json();
  return json.data ?? json;
}

const THREAT_RISK = { normal: 15, suspicious: 45, threatening: 75, critical: 95 };

function normalizeTopology(raw) {
  if (!raw || typeof raw !== 'object') return { nodes: [], edges: [] };
  const rawNodes = Array.isArray(raw.nodes) ? raw.nodes : [];
  const rawEdges = Array.isArray(raw.edges) ? raw.edges : [];
  const nodes = rawNodes.map((n) => {
    const id = n.id || n.service_name || n.container_name || n.name;
    const level = n.threat_level || n.level || 'normal';
    return {
      ...n,
      id,
      name: n.name || n.service_name || id,
      type: n.type || 'service',
      threat_level: level,
      risk_score: n.risk_score ?? THREAT_RISK[level] ?? 15,
      status: n.status || 'running',
      events_count: n.events_count ?? 0,
    };
  });
  const edges = rawEdges.map((e) => ({
    source: typeof e.source === 'string' ? e.source : e.source?.id,
    target: typeof e.target === 'string' ? e.target : e.target?.id,
    type: e.type || e.edge_type,
    observed: !!e.observed,
  }));
  return { nodes, edges, last_updated: raw.last_updated, total_services: raw.total_services };
}

export const api = {
  getEvents: (limit = 100) => request(`/api/events?limit=${limit}`),
  getIncidents: (limit = 50) => request(`/api/incidents?limit=${limit}`),
  getMetrics: () => request('/api/metrics'),
  getRiskScores: () => request('/api/risk-scores'),
  getTopology: () =>
    request('/api/topology')
      .catch(() => request('/topology/graph'))
      .then(normalizeTopology),
  getSystemStatus: () => request('/api/system/status'),
  getProxyConfig: () => request('/api/config/proxy'),
  setProxyConfig: (payload) =>
    authFetch(`${BASE}/api/config/proxy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(async (r) => {
      const j = await r.json();
      if (!r.ok) throw new Error(j.message || `API ${r.status}`);
      return j;
    }),
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
    authFetch(`${BASE}/api/mttd/report`).then(r => r.json()),

  simulateAttack: (scenario) =>
    authFetch(`${BASE}/api/attack/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    }).then(r => r.json()),

  runAttack: (scenario, speed = 'demo') =>
    authFetch(`${BASE}/api/attack/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario, speed }),
    }).then(r => r.json()),

  getAttackStatus: () =>
    authFetch(`${BASE}/api/attack/status`).then(r => r.json()),

  clearEvents: () =>
    authFetch(`${BASE}/api/events/clear`, { method: 'POST' }).then(r => r.json()),

  updateIncidentStatus: (id, status, note = '') =>
    authFetch(`${BASE}/api/incidents/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, note }),
    }).then(r => r.json()),

  // login does NOT use authFetch — no token yet at login time
  login: (username, password) =>
    fetch(`${BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => r.json()),

  // Engine endpoints (Phase 13). The engine listens on :5070; routed through
  // backend /api/engine/* if proxied, else direct.
  getReplaysIndex: () =>
    authFetch(`${BASE}/api/engine/replays`).then(r => r.json()).then(j => j.data ?? j),
  getReplayFrames: (incidentId) =>
    authFetch(`${BASE}/api/engine/replay/${encodeURIComponent(incidentId)}`).then(r => r.json()).then(j => j.data ?? j),
  getMitreHeatmap: () =>
    authFetch(`${BASE}/api/engine/mitre-heatmap`).then(r => r.json()).then(j => j.data ?? j),
  getPredictNext: () =>
    authFetch(`${BASE}/api/engine/predict-next`).then(r => r.json()).then(j => j.data ?? j),
  getEngineAnomalies: () =>
    authFetch(`${BASE}/api/engine/anomalies`).then(r => r.json()).then(j => j.data ?? j),
  getYamlRules: () =>
    authFetch(`${BASE}/api/engine/yaml-rules`).then(r => r.json()).then(j => j.data ?? j),
  getThreatIntelStatus: () =>
    authFetch(`${BASE}/api/engine/threat-intel`).then(r => r.json()).then(j => j.data ?? j),
  getIncidentExplain: (incidentId) =>
    authFetch(`${BASE}/api/engine/incident/${encodeURIComponent(incidentId)}/explain`).then(r => r.json()).then(j => j.data ?? j),
};
