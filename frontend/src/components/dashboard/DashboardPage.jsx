import { useState, useEffect, useMemo, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { buildKpiItems, pickFeaturedIncident } from './dashboardMetrics';
import DemoBanner from './DemoBanner';
import GridDashboard from './GridDashboard';
import ModeSwitcher from './ModeSwitcher';
import StoryDashboard from './StoryDashboard';
import TriageDashboard from './TriageDashboard';

const MODE_KEY = 'securisphere_dashboard_mode';

/**
 * SecuriSphere dashboard shell — triage (default), grid monitoring, or story mode.
 *
 * Data is supplied by realtime hooks upstream (`AuthenticatedApp`); arrays are stable shapes for API wiring.
 *
 * @param {{
 *   events?: Record<string, unknown>[];
 *   incidents?: Record<string, unknown>[];
 *   metrics?: Record<string, unknown>;
 *   timeline?: unknown[];
 *   riskScores?: Record<string, { current_score?: number; threat_level?: string }>;
 * }} props
 */
export default function DashboardPage({
  events = [],
  incidents = [],
  metrics = {},
  timeline = [],
  riskScores = {},
  topology = { nodes: [], edges: [] },
}) {
  const navigate = useNavigate();

  const [mode, setMode] = useState(() => {
    try {
      const s = sessionStorage.getItem(MODE_KEY);
      if (s === 'triage' || s === 'grid' || s === 'story') return s;
    } catch {
      /* ignore */
    }
    return 'triage';
  });

  const [selectedId, setSelectedId] = useState(null);

  /** Re-render cadence so relative timestamps breathe (mock “live” feel). */
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((x) => x + 1), 8000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem(MODE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, [mode]);

  useEffect(() => {
    if (!incidents.length) {
      setSelectedId(null);
      return;
    }
    setSelectedId((prev) => {
      const ids = incidents.map((i) => String(i?.incident_id ?? ''));
      if (prev && ids.includes(prev)) return prev;
      return ids[0] || null;
    });
  }, [incidents]);

  const kpiItems = useMemo(
    () => buildKpiItems({ events, incidents, metrics }),
    [events, incidents, metrics]
  );

  const featured = useMemo(() => pickFeaturedIncident(incidents), [incidents]);

  const onSelectIncident = useCallback((id) => {
    setSelectedId(id);
  }, []);

  const onBlockIp = useCallback(() => {
    const ip = window.prompt('IP address to block (demo workflow):', '10.0.2.4');
    if (ip?.trim()) window.alert(`Queued block for ${ip.trim()} — connect SOAR / firewall API.`);
  }, []);

  const onOpenIncident = useCallback(() => {
    navigate('/incidents');
  }, [navigate]);

  const onAssign = useCallback(() => {
    navigate('/incidents');
  }, [navigate]);

  return (
    <div className="space-y-4 text-base-200">
      <DemoBanner />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-base-100">Operations overview</h1>
          <p className="text-xs text-base-500">Fast triage · clear priorities · minimal noise</p>
        </div>
        <ModeSwitcher mode={mode} onChange={setMode} />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={mode}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {mode === 'triage' && (
            <TriageDashboard
              kpiItems={kpiItems}
              events={events}
              incidents={incidents}
              timeline={timeline}
              topology={topology}
              riskScores={riskScores}
              selectedId={selectedId}
              onSelectIncident={onSelectIncident}
            />
          )}
          {mode === 'grid' && (
            <GridDashboard
              kpiItems={kpiItems}
              events={events}
              incidents={incidents}
              timeline={timeline}
              topology={topology}
              riskScores={riskScores}
              selectedId={selectedId}
              onSelectIncident={onSelectIncident}
            />
          )}
          {mode === 'story' && (
            <StoryDashboard
              kpiItems={kpiItems}
              featured={featured}
              events={events}
              timeline={timeline}
              onBlockIp={onBlockIp}
              onOpenIncident={onOpenIncident}
              onAssign={onAssign}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
