import { useState, useEffect, useCallback, useRef } from 'react';
import { connectSocket, disconnectSocket } from '@/lib/websocket';
import { api } from '@/lib/api';
import { generateFullMockData } from '@/lib/mock-data';

const MAX_EVENTS = 200;
const MAX_INCIDENTS = 100;

// Live-merge event into topology so graph reacts during attack
// without waiting for next 15s topology poll. Adds missing nodes/edges
// derived from source_entity/destination_entity service names and bumps
// per-node events_count so risk styling can react.
function mergeEventIntoTopology(prev, ev) {
  const src = ev?.source_entity?.service;
  const dst = ev?.destination_entity?.service;
  if (!src && !dst) return prev;

  const nodes = (prev.nodes || []).slice();
  const edges = (prev.edges || []).slice();
  const byId = new Map(nodes.map((n, i) => [n.id, i]));

  const ensureNode = (name) => {
    if (!name) return;
    if (byId.has(name)) {
      const i = byId.get(name);
      nodes[i] = { ...nodes[i], events_count: (nodes[i].events_count || 0) + 1, last_event_ts: Date.now() };
      return;
    }
    nodes.push({
      id: name,
      name,
      type: 'service',
      risk_score: 0,
      status: 'running',
      events_count: 1,
      last_event_ts: Date.now(),
    });
    byId.set(name, nodes.length - 1);
  };
  ensureNode(src);
  ensureNode(dst);

  if (src && dst && src !== dst) {
    const exists = edges.some((e) => {
      const s = e.source?.id ?? e.source;
      const t = e.target?.id ?? e.target;
      return s === src && t === dst;
    });
    if (!exists) edges.push({ source: src, target: dst });
  }

  return { ...prev, nodes, edges };
}

export function useRealtime() {
  const [events, setEvents] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [riskScores, setRiskScores] = useState({});
  const [metrics, setMetrics] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [systemStatus, setSystemStatus] = useState({});
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [usingMock, setUsingMock] = useState(false);

  const pollRef = useRef(null);            // legacy catch-all fallback
  const incidentPollRef = useRef(null);    // WS-disconnect fallback for incidents
  const touch = () => setLastUpdate(new Date().toISOString());

  // Incidents are delivered via WebSocket (new_incident). This poller is
  // only active as a fallback when the socket is disconnected.
  const fetchIncidents = useCallback(async () => {
    try {
      const res = await api.getIncidents();
      const list = res?.incidents || res || [];
      setIncidents(list.slice(0, MAX_INCIDENTS));
      touch();
    } catch {
      /* swallow — WS will resume or next tick retries */
    }
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      // Note: incidents intentionally omitted — delivered via WebSocket push.
      const [evRes, riskRes, topoRes, metricsRes, timeRes, sysRes] = await Promise.allSettled([
        api.getEvents(),
        api.getRiskScores(),
        api.getTopology(),
        api.getDashboardSummary(),
        api.getTimeline(),
        api.getSystemStatus(),
      ]);

      if (evRes.status === 'fulfilled') setEvents(evRes.value?.events || evRes.value || []);
      if (riskRes.status === 'fulfilled') setRiskScores(riskRes.value?.risk_scores || riskRes.value || {});
      if (topoRes.status === 'fulfilled') setTopology(topoRes.value || { nodes: [], edges: [] });
      if (metricsRes.status === 'fulfilled') {
        const m = metricsRes.value;
        setMetrics(m?.metrics || m || {});
      }
      if (timeRes.status === 'fulfilled') setTimeline(timeRes.value?.timeline || timeRes.value || []);
      if (sysRes.status === 'fulfilled') setSystemStatus(sysRes.value || {});
      setUsingMock(false);
      touch();
    } catch {
      // Backend offline — use mock data
      const mock = generateFullMockData();
      setEvents(mock.events);
      setIncidents(mock.incidents);
      setRiskScores(mock.riskScores);
      setTopology(mock.topology);
      setMetrics(mock.metrics);
      setTimeline(mock.timeline);
      setUsingMock(true);
      touch();
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket connection
  useEffect(() => {
    const socket = connectSocket({
      onConnect: () => {
        setConnected(true);
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        if (incidentPollRef.current) {
          clearInterval(incidentPollRef.current);
          incidentPollRef.current = null;
        }
      },
      onDisconnect: () => {
        setConnected(false);
        // WS gone — poll incidents at 5s. Other feeds keep their 15s cadence.
        if (!incidentPollRef.current) {
          incidentPollRef.current = setInterval(fetchIncidents, 5000);
        }
      },
      onEvent: (ev) => {
        setEvents(prev => [ev, ...prev].slice(0, MAX_EVENTS));
        setTopology(prev => mergeEventIntoTopology(prev, ev));
        touch();
      },
      onIncident: (inc) => {
        // Primary delivery path — pushed from backend immediately on
        // correlated_incidents pub/sub. Dedupe by incident_id.
        setIncidents(prev => {
          if (inc?.incident_id && prev.some(p => p.incident_id === inc.incident_id)) {
            return prev;
          }
          return [inc, ...prev].slice(0, MAX_INCIDENTS);
        });
        // Splice incident's service_path into topology so the chain shows
        // immediately even if individual events were dropped/missed.
        const path = Array.isArray(inc?.service_path) ? inc.service_path : [];
        if (path.length > 1) {
          setTopology(prev => {
            let next = prev;
            for (let i = 0; i < path.length - 1; i++) {
              next = mergeEventIntoTopology(next, {
                source_entity: { service: path[i] },
                destination_entity: { service: path[i + 1] },
              });
            }
            return next;
          });
        }
        // Pull fresh authoritative topology in the background.
        api.getTopology().then((t) => t && setTopology(t)).catch(() => {});
        touch();
      },
      onRiskUpdate: (data) => {
        setRiskScores(prev => ({ ...prev, [data.ip || data.service]: data.score_data || data }));
        touch();
      },
      onSummary: (data) => { setMetrics(data?.metrics || data); touch(); },
      onMetrics: (data) => { setMetrics(data); touch(); },
      onTimeline: (data) => { setTimeline(data.timeline || []); touch(); },
      onInitialState: (data) => {
        if (data.summary) setMetrics(data.summary?.metrics || data.summary);
        touch();
      },
      onFullRefresh: () => fetchAll(),
      onIncidentStatusChange: (data) => {
        if (data.incident_id && data.status) {
          setIncidents(prev => prev.map(inc =>
            inc.incident_id === data.incident_id ? { ...inc, status: data.status } : inc
          ));
        }
      },
    });

    // Initial fetch — hydrate everything including the incidents list once.
    fetchAll();
    fetchIncidents();

    // Periodic refresh for polled feeds. Incidents polled too (every 15s) as a
    // safety net — WS push is primary but this catches missed pushes.
    const refreshId = setInterval(() => {
      fetchAll();
      fetchIncidents();
    }, 15000);

    return () => {
      clearInterval(refreshId);
      if (pollRef.current) clearInterval(pollRef.current);
      if (incidentPollRef.current) clearInterval(incidentPollRef.current);
      disconnectSocket();
    };
  }, [fetchAll, fetchIncidents]);

  return {
    events, incidents, riskScores, metrics, timeline,
    topology, systemStatus, connected, loading, lastUpdate,
    usingMock, refetch: fetchAll,
    setEvents, setIncidents,
  };
}
