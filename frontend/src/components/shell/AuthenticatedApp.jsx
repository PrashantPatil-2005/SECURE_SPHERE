import { useEffect, useCallback } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useRealtime } from '@/hooks/use-realtime';
import { useAppStore } from '@/stores/useAppStore';
import {
  NAV_SHELL,
  NAV_SHELL_STORAGE_KEY,
  VALID_NAV_SHELLS,
  tabIdFromPath,
  pathForTab,
} from '@/components/nav/navConfig';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Header from '@/components/layout/Header';
import StatusBar from '@/components/layout/StatusBar';
import TweaksPanel from '@/components/shell/TweaksPanel';
import IncidentToaster from '@/components/notifications/IncidentToaster';
import { Skeleton } from '@/components/ui/Spinner';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { readPersistedTheme } from '@/lib/themeDom';
import Dashboard from '@/pages/Dashboard';
import Events from '@/pages/Events';
import Incidents from '@/pages/Incidents';
import Topology from '@/pages/Topology';
import RiskScores from '@/pages/RiskScores';
import System from '@/pages/System';
import Mitre from '@/pages/Mitre';
import Intro from '@/pages/Intro';
import Replay from '@/pages/Replay';

function isTypingTarget(el) {
  if (!el || !(el instanceof Element)) return false;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.getAttribute('contenteditable') === 'true') return true;
  if (el.closest('[role="combobox"]')) return true;
  return false;
}

export default function AuthenticatedApp() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = tabIdFromPath(location.pathname);

  const theme = useAppStore((s) => s.theme);
  const density = useAppStore((s) => s.density);
  const ann = useAppStore((s) => s.ann);
  const nav = useAppStore((s) => s.nav);
  const toggleTweaks = useAppStore((s) => s.toggleTweaks);
  const toggleDensity = useAppStore((s) => s.toggleDensity);
  const toggleAnn = useAppStore((s) => s.toggleAnn);
  const toggleTheme = useAppStore((s) => s.toggleTheme);

  const {
    events, incidents, riskScores, metrics, timeline,
    topology, systemStatus, connected, loading, lastUpdate,
    usingMock, refetch, setEvents, setIncidents,
  } = useRealtime();

  useEffect(() => {
    try {
      if (localStorage.getItem('securisphere-app-store')) return;
      const t = readPersistedTheme();
      if (t) useAppStore.getState().setTheme(t);
      const n = localStorage.getItem(NAV_SHELL_STORAGE_KEY);
      if (n && VALID_NAV_SHELLS.includes(n)) useAppStore.getState().setNav(n);
    } catch {
      /* ignore */
    }
  }, []);

  const handleClear = useCallback(async () => {
    if (!window.confirm('Clear all event data?')) return;
    try {
      await api.clearEvents();
      setEvents([]);
      setIncidents([]);
      setTimeout(refetch, 500);
    } catch (err) {
      console.error('Clear failed:', err);
    }
  }, [refetch, setEvents, setIncidents]);

  const goTab = useCallback((id) => navigate(pathForTab(id)), [navigate]);

  useEffect(() => {
    const handler = (e) => {
      if (isTypingTarget(e.target)) return;
      if (e.defaultPrevented) return;

      if (e.code === 'Digit1') {
        e.preventDefault();
        navigate('/intro');
        return;
      }
      if (e.code === 'Digit2') {
        e.preventDefault();
        navigate('/dashboard');
        return;
      }
      const k = e.key.toLowerCase();
      if (k === 't') {
        e.preventDefault();
        toggleTweaks();
        return;
      }
      if (k === 'd') {
        e.preventDefault();
        toggleDensity();
        return;
      }
      if (k === 'a') {
        e.preventDefault();
        toggleAnn();
        return;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate, toggleTweaks, toggleDensity, toggleAnn]);

  if (loading && events.length === 0) {
    const isTop = nav === NAV_SHELL.TOP;
    return (
      <div
        className={cn(
          'flex min-h-screen flex-col bg-base-950 transition-colors duration-200',
          density === 'compact' && 'text-[13px] leading-snug',
          ann === 'on' && 'show-annotations'
        )}
      >
        {!isTop && <div className="h-12 shrink-0 border-b border-dashed border-base-800 bg-base-900/80" />}
        <div className="flex min-h-0 flex-1 flex-row">
          {nav === NAV_SHELL.SIDEBAR && (
            <div className="w-[130px] shrink-0 border-r border-dashed border-base-800 bg-base-900/80" />
          )}
          <div className="flex min-w-0 flex-1 flex-col">
            {isTop && <div className="h-[52px] shrink-0 border-b border-dashed border-base-800 bg-base-900/80" />}
            <div className="h-12 shrink-0 border-b border-base-800 bg-base-900/60" />
            <div className="flex-1 space-y-4 p-6">
              <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-28 rounded-[10px]" />
                ))}
              </div>
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-64 rounded-[10px]" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'min-h-screen bg-base-950',
        density === 'compact' && 'text-[13px] leading-snug',
        ann === 'on' && 'show-annotations'
      )}
    >
      <DashboardLayout
        shell={nav}
        activeTab={activeTab}
        onTabChange={goTab}
        badges={{ events: events.length, incidents: incidents.length }}
        connected={connected}
        lastUpdate={lastUpdate}
        onProfileClick={() => navigate('/system')}
        toolbar={
          <Header
            incidentCount={incidents.length}
            incidents={incidents}
            theme={theme}
            onToggleTheme={toggleTheme}
            onRefresh={refetch}
            onClear={handleClear}
            onProfileClick={() => navigate('/system')}
            onNavigate={navigate}
          />
        }
        statusBar={
          <StatusBar
            connected={connected}
            lastUpdate={lastUpdate}
            eventCount={events.length}
            incidentCount={incidents.length}
            usingMock={usingMock}
          />
        }
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            <Routes>
              <Route path="/intro" element={<Intro />} />
              <Route
                path="/dashboard"
                element={
                  <Dashboard
                    events={events}
                    incidents={incidents}
                    metrics={metrics}
                    timeline={timeline}
                    riskScores={riskScores}
                    topology={topology}
                  />
                }
              />
              <Route path="/events" element={<Events events={events} />} />
              <Route
                path="/incidents"
                element={<Incidents incidents={incidents} onReplayRequest={() => navigate('/topology')} />}
              />
              <Route
                path="/topology"
                element={<Topology topology={topology} riskScores={riskScores} incidents={incidents} />}
              />
              <Route path="/risk" element={<RiskScores riskScores={riskScores} />} />
              <Route path="/mitre" element={<Mitre />} />
              <Route path="/replay" element={<Replay />} />
              <Route path="/system" element={<System systemStatus={systemStatus} onRefresh={refetch} />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </DashboardLayout>

      <TweaksPanel badges={{ events: events.length, incidents: incidents.length }} />

      <IncidentToaster incidents={incidents} />
    </div>
  );
}
