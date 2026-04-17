import { useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTheme } from '@/hooks/use-theme';
import { useRealtime } from '@/hooks/use-realtime';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import StatusBar from '@/components/layout/StatusBar';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Events from '@/pages/Events';
import Incidents from '@/pages/Incidents';
import Topology from '@/pages/Topology';
import RiskScores from '@/pages/RiskScores';
import System from '@/pages/System';
import { Skeleton } from '@/components/ui/Spinner';
import { api } from '@/lib/api';

export default function App() {
  // Theme
  const { theme, toggle: toggleTheme } = useTheme();

  // Auth
  const [authed, setAuthed] = useState(() =>
    !!(localStorage.getItem('securisphere_token') || sessionStorage.getItem('securisphere_token'))
  );
  const handleLogin = useCallback(() => setAuthed(true), []);

  // Tab routing
  const [tab, setTab] = useState('dashboard');

  // Real-time data
  const {
    events, incidents, riskScores, metrics, timeline,
    topology, systemStatus, connected, loading, lastUpdate,
    usingMock, refetch, setEvents, setIncidents,
  } = useRealtime();

  // Handlers
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

  const handleReplayRequest = useCallback((incidentId) => {
    setTab('topology');
  }, []);

  // Auth gate
  if (!authed) {
    return <Login onLogin={handleLogin} />;
  }

  // Loading skeleton
  if (loading && events.length === 0) {
    return (
      <div className="flex min-h-screen bg-base-950">
        <div className="w-16 bg-base-900 border-r border-white/[0.05]" />
        <div className="flex-1 flex flex-col">
          <div className="h-12 border-b border-white/[0.05] bg-base-900/80" />
          <div className="flex-1 p-6 space-y-4">
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-28 rounded-[10px]" />)}
            </div>
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map(i => <Skeleton key={i} className="h-64 rounded-[10px]" />)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const renderTab = () => {
    switch (tab) {
      case 'dashboard':
        return <Dashboard events={events} incidents={incidents} metrics={metrics} timeline={timeline} riskScores={riskScores} />;
      case 'events':
        return <Events events={events} />;
      case 'incidents':
        return <Incidents incidents={incidents} onReplayRequest={handleReplayRequest} />;
      case 'topology':
        return <Topology topology={topology} riskScores={riskScores} incidents={incidents} />;
      case 'risk':
        return <RiskScores riskScores={riskScores} />;
      case 'system':
        return <System systemStatus={systemStatus} onRefresh={refetch} />;
      default:
        return <Dashboard events={events} incidents={incidents} metrics={metrics} timeline={timeline} riskScores={riskScores} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-base-950 dark:bg-base-950">
      <Sidebar
        activeTab={tab}
        onTabChange={setTab}
        badges={{ events: events.length, incidents: incidents.length }}
        connected={connected}
      />

      <div className="flex flex-col flex-1 ml-16 min-h-screen transition-all duration-200">
        <Header
          connected={connected}
          lastUpdate={lastUpdate}
          incidentCount={incidents.length}
          theme={theme}
          onToggleTheme={toggleTheme}
          onRefresh={refetch}
          onClear={handleClear}
          onProfileClick={() => setTab('system')}
        />

        <main className="flex-1 p-6 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              {renderTab()}
            </motion.div>
          </AnimatePresence>
        </main>

        <StatusBar
          connected={connected}
          lastUpdate={lastUpdate}
          eventCount={events.length}
          incidentCount={incidents.length}
          usingMock={usingMock}
        />
      </div>
    </div>
  );
}
