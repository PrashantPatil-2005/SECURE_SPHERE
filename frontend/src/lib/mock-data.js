const SERVICES = [
  'auth-service', 'api-gateway', 'payment-service',
  'user-service', 'inventory-service', 'frontend',
];

const EVENT_TYPES = [
  'brute_force_attempt', 'sql_injection', 'port_scan',
  'path_traversal', 'credential_stuffing', 'xss_attempt',
  'privilege_escalation', 'lateral_movement', 'data_exfiltration',
  'suspicious_traffic', 'failed_login', 'token_replay',
];

const LAYERS = ['network', 'api', 'auth', 'browser'];
const SEVERITIES = ['critical', 'high', 'medium', 'low'];
const MITRE_IDS = [
  'T1110', 'T1078', 'T1021', 'T1068', 'T1046',
  'T1041', 'T1595', 'T1190', 'T1003', 'T1530',
];

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function randIP() { return `10.0.${Math.floor(Math.random() * 5)}.${Math.floor(Math.random() * 254) + 1}`; }
function randId() { return `evt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`; }

export function generateMockEvent(index = 0) {
  const now = new Date(Date.now() - index * 3000);
  return {
    event_id: randId(),
    event_type: pick(EVENT_TYPES),
    timestamp: now.toISOString(),
    source_layer: pick(LAYERS),
    severity: { level: pick(SEVERITIES), score: Math.floor(Math.random() * 100) },
    source_entity: { ip: randIP(), service: pick(SERVICES) },
    destination_entity: { ip: randIP(), service: pick(SERVICES) },
    mitre_technique: pick(MITRE_IDS),
    confidence: Math.floor(Math.random() * 40 + 60),
    details: { message: `Detected ${pick(EVENT_TYPES)} from ${pick(SERVICES)}` },
  };
}

export function generateMockIncident(index = 0) {
  const sev = pick(SEVERITIES);
  const steps = Math.floor(Math.random() * 4) + 2;
  return {
    incident_id: `inc_${1000 + index}`,
    title: `${pick(['Multi-Stage Attack', 'Brute Force Campaign', 'Lateral Movement', 'Data Exfiltration', 'Recon + Exploit'])} — ${pick(SERVICES)}`,
    severity: sev,
    status: pick(['open', 'investigating', 'resolved']),
    timestamp: new Date(Date.now() - index * 60000).toISOString(),
    layers_involved: [...new Set([pick(LAYERS), pick(LAYERS)])],
    mitre_techniques: [...new Set([pick(MITRE_IDS), pick(MITRE_IDS)])],
    event_count: Math.floor(Math.random() * 20 + 3),
    kill_chain_steps: steps,
    mttd_seconds: Math.floor(Math.random() * 30 + 2),
    service_path: Array.from({ length: steps }, () => pick(SERVICES)),
    source_ip: randIP(),
  };
}

export function generateMockRiskScores() {
  const scores = {};
  SERVICES.forEach(svc => {
    const score = Math.floor(Math.random() * 180);
    const level = score > 150 ? 'critical' : score > 70 ? 'threatening' : score > 30 ? 'suspicious' : 'normal';
    scores[svc] = {
      current_score: score,
      threat_level: level,
      last_updated: new Date().toISOString(),
      event_count: Math.floor(Math.random() * 50),
      top_events: [pick(EVENT_TYPES), pick(EVENT_TYPES)],
    };
  });
  return scores;
}

export function generateMockTopology() {
  return {
    nodes: SERVICES.map(name => ({
      id: name,
      name,
      type: 'service',
      risk_score: Math.floor(Math.random() * 150),
      status: pick(['running', 'running', 'running', 'degraded']),
      events_count: Math.floor(Math.random() * 30),
    })),
    edges: [
      { source: 'frontend', target: 'api-gateway' },
      { source: 'api-gateway', target: 'auth-service' },
      { source: 'api-gateway', target: 'user-service' },
      { source: 'api-gateway', target: 'payment-service' },
      { source: 'api-gateway', target: 'inventory-service' },
      { source: 'user-service', target: 'auth-service' },
      { source: 'payment-service', target: 'user-service' },
    ],
  };
}

export function generateMockMetrics() {
  return {
    raw_events: { total: Math.floor(Math.random() * 500 + 100) },
    alert_reduction_percentage: Math.floor(Math.random() * 30 + 60),
    events_per_second: (Math.random() * 5 + 0.5).toFixed(1),
    total_incidents: Math.floor(Math.random() * 15),
  };
}

export function generateFullMockData() {
  return {
    events: Array.from({ length: 50 }, (_, i) => generateMockEvent(i)),
    incidents: Array.from({ length: 6 }, (_, i) => generateMockIncident(i)),
    riskScores: generateMockRiskScores(),
    topology: generateMockTopology(),
    metrics: generateMockMetrics(),
    timeline: Array.from({ length: 30 }, (_, i) => ({
      timestamp: new Date(Date.now() - (29 - i) * 2000).toISOString(),
      events: Math.floor(Math.random() * 10 + 1),
      critical: Math.floor(Math.random() * 3),
      high: Math.floor(Math.random() * 4),
      medium: Math.floor(Math.random() * 5),
      low: Math.floor(Math.random() * 6),
    })),
  };
}
