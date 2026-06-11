import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Bell, Sun, Moon, RefreshCw, Trash2, Loader2, Terminal, Bot } from 'lucide-react';
import { api } from '@/lib/api';
import { useOpenCommandPalette } from '@/contexts/CommandPaletteBridge';
import { useAuth } from '@/contexts/AuthProvider';
import ProfileMenu from '@/components/layout/ProfileMenu';

const PATH_LABELS = {
  '/dashboard': ['Operations Overview', 'Triage Mode'],
  '/events':    ['Live Events', 'Stream'],
  '/incidents': ['Incidents', 'Investigation'],
  '/campaigns': ['Campaigns', 'Correlation'],
  '/evaluation':['Evaluation', 'MTTD Results'],
  '/topology':  ['Topology', 'Service Graph'],
  '/risk':      ['Risk Scores', 'Per-service'],
  '/mitre':     ['MITRE ATT&CK', 'Coverage'],
  '/replay':    ['Replay', 'Scenario'],
  '/audit':     ['Audit', 'Logs'],
  '/system':    ['System', 'Health'],
  '/settings':  ['Settings', 'Preferences'],
  '/users':     ['Users', 'Management'],
};

export default function Header({
  incidentCount = 0,
  criticalCount,
  highCount,
  systemStatus = 'NOMINAL',
  unreadCount = 0,
  theme,
  onToggleTheme,
  onRefresh,
  onClear,
  onProfileClick,
  onNavigate,
  onLogout,
  onOpenNotifications,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [primary, secondary] = PATH_LABELS[location.pathname] || ['SecuriSphere', ''];
  const { openPalette } = useOpenCommandPalette();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [clock, setClock] = useState(new Date());

  // Derived user display values
  const userInitial = (user?.username?.[0] || user?.email?.[0] || 'U').toUpperCase();
  const userLabel = user?.username || user?.email || 'Profile';

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await api.globalSearch(searchQuery.trim(), 5);
        setSearchResults(res.results || []);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const handleResultClick = (res) => {
    const isIncident = !!(res.incident_id || res.scenario_label);
    const id = res.incident_id || res.event_id;
    const path = isIncident ? '/incidents' : '/events';
    const dest = id ? `${path}?focus=${encodeURIComponent(id)}` : path;
    setSearchQuery('');
    setSearchResults(null);
    navigate(dest);
  };

  const handleToggleAiChat = () => {
    document.dispatchEvent(new CustomEvent('toggle-ai-chat'));
  };

  return (
    <header className="sticky top-0 z-40 flex h-12 items-center justify-between gap-3 border-b border-base-800 bg-base-950/95 px-5 backdrop-blur-xl transition-colors duration-200">
      {/* Left: breadcrumb */}
      <div className="flex min-w-0 shrink-0 items-center gap-2">
        <span className="truncate text-sm font-semibold tracking-tight text-base-100">{primary}</span>
        {secondary && (
          <>
            <span className="text-base-700" aria-hidden="true">·</span>
            <span className="type-caption truncate">{secondary}</span>
          </>
        )}
      </div>

      {/* Center: severity pills */}
      <div className="hidden items-center gap-1.5 md:flex">
        {typeof criticalCount === 'number' && criticalCount > 0 && (
          <div
            className="flex items-center gap-1.5 rounded-full border px-2.5 py-1"
            style={{ background: 'var(--sev-critical-bg)', borderColor: 'var(--sev-critical-border)' }}
          >
            <span
              className="dot-pulse inline-block h-1.5 w-1.5 rounded-full"
              style={{ background: 'var(--sev-critical)', '--dot-color': 'rgba(239,68,68,0.6)' }}
            />
            <span className="type-data text-[11px] font-bold" style={{ color: 'var(--sev-critical)' }}>
              {criticalCount}
            </span>
            <span className="type-eyebrow opacity-90" style={{ color: 'var(--sev-critical)' }}>
              Critical
            </span>
          </div>
        )}
        {typeof highCount === 'number' && highCount > 0 && (
          <div
            className="flex items-center gap-1.5 rounded-full border px-2.5 py-1"
            style={{ background: 'var(--sev-high-bg)', borderColor: 'var(--sev-high-border)' }}
          >
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ background: 'var(--sev-high)' }}
            />
            <span className="type-data text-[11px] font-bold" style={{ color: 'var(--sev-high)' }}>
              {highCount}
            </span>
            <span className="type-eyebrow opacity-90" style={{ color: 'var(--sev-high)' }}>
              High
            </span>
          </div>
        )}
        <div
          className="flex items-center gap-1.5 rounded-full border px-3 py-1"
          style={{
            background: systemStatus === 'NOMINAL' ? 'rgba(52,211,153,0.08)' : 'rgba(239,68,68,0.08)',
            borderColor: systemStatus === 'NOMINAL' ? 'rgba(52,211,153,0.22)' : 'rgba(239,68,68,0.22)',
          }}
        >
          <span
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{
              background: systemStatus === 'NOMINAL' ? '#34d399' : '#ef4444',
              boxShadow: systemStatus === 'NOMINAL' ? '0 0 6px #34d399' : '0 0 6px #ef4444',
            }}
          />
          <span
            className="type-eyebrow font-bold"
            style={{ color: systemStatus === 'NOMINAL' ? '#34d399' : '#ef4444' }}
          >
            {systemStatus}
          </span>
        </div>
      </div>

      {/* Right: actions */}
      <div className="flex min-w-0 shrink-0 items-center gap-1.5">
        {/* Command palette */}
        <Button
          variant="secondary"
          size="sm"
          className="h-8 shrink-0 gap-1.5 border-base-800 px-2 text-2xs text-base-400"
          onClick={openPalette}
          title="Command palette (⌘K)"
        >
          <Terminal className="h-3.5 w-3.5 text-accent/80" />
          <span className="hidden sm:inline">⌘K</span>
        </Button>

        {/* Global search */}
        <div className="relative hidden min-w-0 max-w-[240px] flex-1 items-center lg:flex" role="search">
          <input
            type="search"
            placeholder="Global search…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Global search"
            className="h-8 w-full rounded-md border border-dashed border-base-800 bg-base-950/40 px-3 font-mono text-xs tabular-nums text-base-200 outline-none transition-colors duration-200 placeholder:text-base-600 focus:border-accent/35 focus-visible:ring-2 focus-visible:ring-accent/40"
          />
          {searchQuery.trim() !== '' && searchResults !== null && (
            <div className="absolute left-0 right-0 top-10 z-50 max-h-80 overflow-y-auto rounded-lg border border-base-800 bg-base-900 p-2 shadow-xl transition-colors duration-200">
              {isSearching ? (
                <div className="flex items-center justify-center gap-2 p-4 text-xs text-base-500">
                  <Loader2 className="h-4 w-4 animate-spin text-accent" /> Searching…
                </div>
              ) : searchResults.length > 0 ? (
                searchResults.map((res, idx) => (
                  <div
                    key={res.event_id || res.incident_id || idx}
                    className="cursor-pointer rounded-md p-2 transition-colors duration-200 hover:bg-base-950/50"
                    onClick={() => handleResultClick(res)}
                  >
                    <div className="text-xs font-medium text-base-200">
                      {res.title || res.scenario_label || res.event_type || 'Unknown'}
                    </div>
                    <div className="type-data mt-0.5 truncate text-2xs text-base-500">
                      {res.source_ip
                        ? `IP: ${res.source_ip}`
                        : res.severity?.level
                          ? `Severity: ${res.severity.level}`
                          : res.source_layer || 'Event'}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-base-500">No matches</div>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {/* Notifications */}
          <Button
            variant="icon"
            size="icon"
            title="Notifications"
            aria-label={incidentCount > 0 ? `Notifications, ${incidentCount} active` : 'Notifications'}
            aria-haspopup="dialog"
            onClick={onOpenNotifications}
            className="relative"
          >
            <Bell className={cn('h-3.5 w-3.5', unreadCount > 0 && 'animate-[wiggle_1.5s_ease-in-out_infinite]')} />
            {incidentCount > 0 && (
              <span
                aria-hidden="true"
                className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full border border-base-900 bg-red-500 px-1 text-[8px] font-bold text-white shadow-[0_0_8px_rgba(239,68,68,0.7)]"
              >
                {incidentCount > 99 ? '99+' : incidentCount}
              </span>
            )}
          </Button>

          {/* AI Chat */}
          <Button
            variant="icon"
            size="icon"
            onClick={handleToggleAiChat}
            title="AI Analyst Chat"
            aria-label="Open AI analyst chat"
          >
            <Bot className="h-3.5 w-3.5" />
          </Button>

          {/* Theme toggle */}
          <Button
            type="button"
            variant="icon"
            size="icon"
            onClick={() => onToggleTheme?.()}
            title="Toggle light / dark theme"
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            aria-pressed={theme === 'dark'}
          >
            {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </Button>

          {/* Refresh */}
          <Button variant="icon" size="icon" onClick={onRefresh} title="Refresh" aria-label="Refresh data">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>

          {/* Clear */}
          <Button
            variant="icon"
            size="icon"
            onClick={onClear}
            title="Clear data"
            aria-label="Clear data"
            className="text-base-500 hover:text-base-200"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>

          <div className="mx-1 hidden h-5 w-px bg-base-800 sm:block" />

          {/* Clock */}
          <span className="type-data hidden sm:inline text-xs text-base-400">
            {clock.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>

          {/* Profile */}
          <ProfileMenu
            initial={userInitial}
            label={userLabel}
            onNavigate={(p) => (onNavigate ? onNavigate(p) : onProfileClick?.())}
            onLogout={onLogout}
          />
        </div>
      </div>
    </header>
  );
}
