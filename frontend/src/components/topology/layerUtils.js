/** SOC-style logical tiers for dependency visualization (heuristic from node id/name). */
export const LAYER_IDS = {
  EDGE: 'edge',
  APP: 'app',
  DATA: 'data',
};

const LAYER_ORDER = [LAYER_IDS.EDGE, LAYER_IDS.APP, LAYER_IDS.DATA];

export function layerForNode(node) {
  const n = `${node?.name || node?.id || ''}`.toLowerCase();
  /* Ingress / client only — API gateways live in the app tier for east–west context */
  if (n.includes('frontend') || n.includes('browser') || n.includes('cdn') || /^edge-/.test(n)) {
    return LAYER_IDS.EDGE;
  }
  if (
    n.includes('database') ||
    n.includes('db-') ||
    n.includes('redis') ||
    n.includes('postgres') ||
    n.includes('mongo') ||
    n.includes('storage') ||
    n.includes('s3')
  ) {
    return LAYER_IDS.DATA;
  }
  return LAYER_IDS.APP;
}

export function enrichNodesWithLayer(nodes, riskScores = {}) {
  return (nodes || []).map((n) => {
    const risk = riskScores[n.id]?.current_score ?? n.risk_score ?? 0;
    const level = riskScores[n.id]?.threat_level ?? 'normal';
    return {
      ...n,
      risk,
      level,
      layer: layerForNode(n),
    };
  });
}

export function groupNodesByLayer(enrichedNodes) {
  const map = { [LAYER_IDS.EDGE]: [], [LAYER_IDS.APP]: [], [LAYER_IDS.DATA]: [] };
  enrichedNodes.forEach((n) => {
    const L = n.layer || LAYER_IDS.APP;
    if (map[L]) map[L].push(n);
    else map[LAYER_IDS.APP].push(n);
  });
  return LAYER_ORDER.map((id) => ({ id, nodes: map[id] || [] }));
}

/** In/out edge lists for sidebar (string ids). */
export function edgesForNode(nodeId, edges = []) {
  const inE = [];
  const outE = [];
  edges.forEach((e) => {
    const s = typeof e.source === 'string' ? e.source : e.source?.id;
    const t = typeof e.target === 'string' ? e.target : e.target?.id;
    if (t === nodeId) inE.push(s);
    if (s === nodeId) outE.push(t);
  });
  return { inEdges: inE, outEdges: outE };
}

export const LAYER_META = {
  [LAYER_IDS.EDGE]: { title: 'Edge / Browser', subtitle: 'Ingress & clients' },
  [LAYER_IDS.APP]: { title: 'App / Services', subtitle: 'East–west workload graph' },
  [LAYER_IDS.DATA]: { title: 'Data', subtitle: 'Persistence & caches' },
};
