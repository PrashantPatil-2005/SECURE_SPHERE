import { useState, useEffect, useRef } from 'react';
import { cn, relativeTime, severityColor, getSeverityString } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Bell, Sun, Moon, RefreshCw, Trash2, Loader2, Terminal, ArrowRight, CheckCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { useOpenCommandPalette } from '@/contexts/CommandPaletteBridge';

export default function Header({
  incidentCount = 0,
  incidents = [],
  theme,
  onToggleTheme,
  onRefresh,
  onClear,
  onProfileClick,
  onNavigate,
}) {
  const { openPalette } = useOpenCommandPalette();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [clock, setClock] = useState(new Date());
  const [bellOpen, setBellOpen] = useState(false);
  const [seenCount, setSeenCount] = useState(0);
  const bellRef = useRef(null);

  const unreadCount = Math.max(0, incidentCount - seenCount);

  useEffect(() => {
    if (!bellOpen) return;
    const onDocClick = (e) => {
      if (bellRef.current && !bellRef.current.contains(e.target)) setBellOpen(false);
    };
    const onEsc = (e) => { if (e.key === 'Escape') setBellOpen(false); };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onEsc);
    };
  }, [bellOpen]);

  const handleBellClick = () => {
    setBellOpen((v) => !v);
    if (!bellOpen) setSeenCount(incidentCount);
  };

  const recent = [...incidents]
    .sort((a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0))
    .slice(0, 6);

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

  return (
    <header className="sticky top-0 z-40 flex h-12 items-center justify-between gap-3 border-b border-dashed border-base-800 bg-base-900/75 px-4 backdrop-blur-xl transition-colors duration-200">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          className="h-8 shrink-0 gap-1.5 border-dashed border-base-800 px-2 font-mono text-[10px] text-base-400"
          onClick={openPalette}
          title="Command palette (⌘K)"
        >
          <Terminal className="h-3.5 w-3.5 text-accent/80" />
          <span className="hidden sm:inline">Commands</span>
          <kbd className="ml-1.5 hidden items-center gap-0.5 rounded-md border border-base-700 bg-base-800/50 px-1.5 py-0.5 font-mono text-[10px] font-medium text-base-200 shadow-sm transition-colors group-hover:border-accent/40 md:inline-flex">
            <span className="text-[11px] opacity-70">
              {typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}
            </span>
            <span>K</span>
          </kbd>
        </Button>

        <div className="relative hidden min-w-0 max-w-md flex-1 items-center sm:flex">
          <input
            type="text"
            placeholder="Global search…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 w-full rounded-md border border-dashed border-base-800 bg-base-950/40 px-3 font-mono text-[11px] text-base-200 outline-none transition-colors duration-200 placeholder:text-base-600 focus:border-accent/35"
          />
          {(searchQuery.trim() !== '' && searchResults !== null) && (
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
                    onClick={() => {
                      setSearchQuery('');
                      setSearchResults(null);
                    }}
                  >
                    <div className="text-[11px] font-semibold text-base-200">
                      {res.title || res.scenario_label || res.event_type || 'Unknown'}
                    </div>
                    <div className="mt-0.5 truncate font-mono text-[10px] text-base-500">
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
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <div ref={bellRef} className="relative">
          <Button
            variant="icon"
            size="icon"
            title="Alerts"
            className={cn('relative', bellOpen && 'bg-accent/10 text-accent')}
            onClick={handleBellClick}
            aria-expanded={bellOpen}
            aria-haspopup="dialog"
          >
            <Bell className={cn('h-3.5 w-3.5', unreadCount > 0 && 'animate-[wiggle_1.5s_ease-in-out_infinite]')} />
            {incidentCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full border border-base-900 bg-red-500 px-1 text-[8px] font-bold text-white shadow-[0_0_8px_rgba(239,68,68,0.7)]">
                {incidentCount > 99 ? '99+' : incidentCount}
              </span>
            )}
          </Button>

          {bellOpen && (
            <div
              role="dialog"
              aria-label="Alerts"
              className="absolute right-0 top-10 z-50 w-80 origin-top-right animate-scale-in rounded-lg border border-base-800 bg-base-900/95 shadow-2xl backdrop-blur-xl"
            >
              <div className="flex items-center justify-between border-b border-dashed border-base-800 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="relative inline-flex h-2 w-2">
                    {incidentCount > 0 && (
                      <span className="absolute inset-0 animate-ping rounded-full bg-red-500 opacity-75" />
                    )}
                    <span className={cn('relative inline-flex h-2 w-2 rounded-full', incidentCount > 0 ? 'bg-red-500' : 'bg-emerald-500')} />
                  </span>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wider text-base-200">Alerts</h3>
                  <span className="font-mono text-[10px] tabular-nums text-base-500">{incidentCount}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSeenCount(incidentCount)}
                  disabled={unreadCount === 0}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-base-400 hover:bg-base-800/60 hover:text-base-200 disabled:opacity-40 disabled:cursor-not-allowed"
                  title="Mark all as seen"
                >
                  <CheckCheck className="h-3 w-3" />
                  Mark seen
                </button>
              </div>

              <div className="max-h-80 overflow-y-auto">
                {recent.length === 0 ? (
                  <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                    <CheckCheck className="h-6 w-6 text-emerald-400" />
                    <p className="text-[11px] text-base-400">No active incidents</p>
                    <p className="text-[10px] text-base-600">All clear.</p>
                  </div>
                ) : (
                  <ul className="divide-y divide-dashed divide-base-800">
                    {recent.map((inc, i) => {
                      const sev = getSeverityString(inc.severity);
                      const c = severityColor(inc.severity);
                      return (
                        <li key={inc.incident_id || inc.id || i}>
                          <button
                            type="button"
                            onClick={() => {
                              setBellOpen(false);
                              onNavigate?.('/incidents');
                            }}
                            className="group flex w-full items-start gap-2 px-3 py-2 text-left transition-colors hover:bg-base-800/40"
                          >
                            <span
                              className="mt-1 h-2 w-2 shrink-0 rounded-full"
                              style={{ backgroundColor: c, boxShadow: `0 0 6px ${c}88` }}
                            />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <span
                                  className="text-[9px] font-semibold uppercase tracking-wider"
                                  style={{ color: c }}
                                >
                                  {sev}
                                </span>
                                <span className="font-mono text-[9px] text-base-600">
                                  {relativeTime(inc.created_at || inc.timestamp)}
                                </span>
                              </div>
                              <p className="mt-0.5 truncate text-[11px] text-base-200 group-hover:text-base-100">
                                {inc.title || inc.scenario_label || inc.description || 'Incident'}
                              </p>
                              {inc.source_ip && (
                                <p className="mt-0.5 truncate font-mono text-[10px] text-base-500">
                                  {inc.source_ip}
                                </p>
                              )}
                            </div>
                            <ArrowRight className="mt-1 h-3 w-3 shrink-0 text-base-600 transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <div className="border-t border-dashed border-base-800 p-2">
                <button
                  type="button"
                  onClick={() => {
                    setBellOpen(false);
                    onNavigate?.('/incidents');
                  }}
                  className="flex w-full items-center justify-center gap-1.5 rounded-md py-1.5 text-[11px] font-medium text-accent transition-colors hover:bg-accent/10"
                >
                  View all incidents
                  <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          )}
        </div>

        <Button type="button" variant="icon" size="icon" onClick={() => onToggleTheme?.()} title="Toggle light / dark theme">
          {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </Button>

        <Button variant="icon" size="icon" onClick={onRefresh} title="Refresh">
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>

        <Button
          variant="icon"
          size="icon"
          onClick={onClear}
          title="Clear data"
          className="text-base-500 hover:text-base-200"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>

        <div className="mx-1 hidden h-5 w-px bg-base-800 sm:block" />

        <span className="hidden font-mono text-[10px] tabular-nums text-base-500 sm:inline w-14 text-right">
          {clock.toLocaleTimeString()}
        </span>

        <div
          role="button"
          tabIndex={0}
          onClick={onProfileClick}
          onKeyDown={(e) => e.key === 'Enter' && onProfileClick?.()}
          className={cn(
            'ml-1 flex h-7 w-7 cursor-pointer items-center justify-center rounded-md',
            'bg-gradient-to-br from-accent to-base-700 text-[11px] font-bold text-base-950',
            'ring-offset-2 ring-offset-base-900 hover:ring-2 hover:ring-accent/30'
          )}
          title="System / profile"
        >
          A
        </div>
      </div>
    </header>
  );
}
