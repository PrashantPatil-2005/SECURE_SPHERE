import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Bell, Sun, Moon, RefreshCw, Trash2, Loader2, Terminal } from 'lucide-react';
import { api } from '@/lib/api';
import { useOpenCommandPalette } from '@/contexts/CommandPaletteBridge';

export default function Header({
  incidentCount = 0,
  theme,
  onToggleTheme,
  onRefresh,
  onClear,
  onProfileClick,
}) {
  const { openPalette } = useOpenCommandPalette();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [clock, setClock] = useState(new Date());

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
          <kbd className="ml-0.5 hidden rounded border border-base-800 bg-base-950 px-1 py-0.5 text-[9px] text-base-500 md:inline">
            {typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}
            K
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
        <Button variant="icon" size="icon" title="Alerts" className="relative">
          <Bell className="h-3.5 w-3.5" />
          {incidentCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border border-base-900 bg-accent" />
          )}
        </Button>

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
