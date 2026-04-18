import { useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTheme } from '@/hooks/use-theme';
import { useRealtime } from '@/hooks/use-realtime';
import { useNavShell } from '@/hooks/useNavShell';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Header from '@/components/layout/Header';
import StatusBar from '@/components/layout/StatusBar';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Events from '@/pages/Events';
import Incidents from '@/pages/Incidents';
import Topology from '@/pages/Topology';
import RiskScores from '@/pages/RiskScores';
import System from '@/pages/System';
import Mitre from '@/pages/Mitre';
import { Skeleton } from '@/components/ui/Spinner';
import { api } from '@/lib/api';
import { NAV_SHELL } from '@/components/nav/navConfig';

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme();
  const { shell, setShell } = useNavShell();

  const [authed, setAuthed] = useState(() =>
    !!(localStorage.getItem('securisphere_token') || sessionStorage.getItem('securisphere_token'))
  );
  const handleLogin = useCallback(() => setAuthed(true), []);

  const [tab, setTab] = useState('dashboard');

  const {
    events, incidents, riskScores, metrics, timeline,
    topology, systemStatus, connected, loading, lastUpdate,
    usingMock, refetch, setEvents, setIncidents,
  } = useRealtime();

  const handleClear = async () => {
    if (!window.confirm('Clear all event data?')) return;
    try {
      await api.clearEvents();
      setEvents([]);
      setIncidents([]);
      setTimeout(refetch, 500);
    } catch (err) {
      console.error('Clear failed:', err);
    }
  };

  const handleReplayRequest = useCallback(() => {
    setTab('topology');
  }, []);

  if (!authed) {
    return <Login onLogin={handleLogin} />;
  }

  if (loading && events.length === 0) {
    const isTop = shell === NAV_SHELL.TOP;
    return (
      <div className="flex min-h-screen flex-col bg-base-950">
        {!isTop && <div className="h-12 shrink-0 border-b border-dashed border-white/[0.06] bg-base-900/80" />}
        <div className="flex min-h-0 flex-1 flex-row">
          {shell === NAV_SHELL.SIDEBAR && (
            <div className="w-[130px] shrink-0 border-r border-dashed border-white/[0.06] bg-base-900/80" />
          )}
          <div className="flex min-w-0 flex-1 flex-col">
            {isTop && <div className="h-[52px] shrink-0 border-b border-dashed border-white/[0.06] bg-base-900/80" />}
            <div className="h-12 shrink-0 border-b border-white/[0.05] bg-base-900/60" />
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

  const renderTab = () => {
    switch (tab) {
      case 'dashboard':
        return (
          <Dashboard
            events={events}
            incidents={incidents}
            metrics={metrics}
            timeline={timeline}
            riskScores={riskScores}
          />
        );
      case 'events':
        return <Events events={events} />;
      case 'incidents':
        return <Incidents incidents={incidents} onReplayRequest={handleReplayRequest} />;
      case 'topology':
        return <Topology topology={topology} riskScores={riskScores} incidents={incidents} />;
      case 'risk':
        return <RiskScores riskScores={riskScores} />;
      case 'mitre':
        return <Mitre />;
      case 'system':
        return (
          <System
            systemStatus={systemStatus}
            onRefresh={refetch}
            navShell={shell}
            onNavShellChange={setShell}
          />
        );
      default:
        return (
          <Dashboard
            events={events}
            incidents={incidents}
            metrics={metrics}
            timeline={timeline}
            riskScores={riskScores}
          />
        );
    }
  };

  return (
    <DashboardLayout
      shell={shell}
      activeTab={tab}
      onTabChange={setTab}
      badges={{ events: events.length, incidents: incidents.length }}
      connected={connected}
      lastUpdate={lastUpdate}
      onProfileClick={() => setTab('system')}
      toolbar={
        <Header
          incidentCount={incidents.length}
          theme={theme}
          onToggleTheme={toggleTheme}
          onRefresh={refetch}
          onClear={handleClear}
          onProfileClick={() => setTab('system')}
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
          key={tab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.18 }}
        >
          {renderTab()}
        </motion.div>
      </AnimatePresence>
    </DashboardLayout>
  );
}
