import { useState, useEffect, useCallback, useRef } from 'react';
import { connectSocket, disconnectSocket } from '@/lib/websocket';
import { api } from '@/lib/api';
import { generateFullMockData } from '@/lib/mock-data';

const MAX_EVENTS = 200;
const MAX_INCIDENTS = 100;

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

  const pollRef = useRef(null);
  const touch = () => setLastUpdate(new Date().toISOString());

  const fetchAll = useCallback(async () => {
    try {
      const [evRes, incRes, riskRes, topoRes, metricsRes, timeRes, sysRes] = await Promise.allSettled([
        api.getEvents(),
        api.getIncidents(),
        api.getRiskScores(),
        api.getTopology(),
        api.getDashboardSummary(),
        api.getTimeline(),
        api.getSystemStatus(),
      ]);

      if (evRes.status === 'fulfilled') setEvents(evRes.value?.events || evRes.value || []);
      if (incRes.status === 'fulfilled') setIncidents(incRes.value?.incidents || incRes.value || []);
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
        if (pollRef.current) clearInterval(pollRef.current);
      },
      onDisconnect: () => {
        setConnected(false);
        // Fall back to polling
        pollRef.current = setInterval(fetchAll, 3000);
      },
      onEvent: (ev) => {
        setEvents(prev => [ev, ...prev].slice(0, MAX_EVENTS));
        touch();
      },
      onIncident: (inc) => {
        setIncidents(prev => [inc, ...prev].slice(0, MAX_INCIDENTS));
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

    // Initial fetch
    fetchAll();

    // Periodic refresh
    const refreshId = setInterval(fetchAll, 15000);

    return () => {
      clearInterval(refreshId);
      if (pollRef.current) clearInterval(pollRef.current);
      disconnectSocket();
    };
  }, [fetchAll]);

  return {
    events, incidents, riskScores, metrics, timeline,
    topology, systemStatus, connected, loading, lastUpdate,
    usingMock, refetch: fetchAll,
    setEvents, setIncidents,
  };
}
