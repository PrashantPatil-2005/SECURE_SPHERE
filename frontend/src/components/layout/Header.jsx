import { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Search, Bell, Sun, Moon, RefreshCw, Trash2, Loader2
} from 'lucide-react';
import { api } from '@/lib/api';

export default function Header({ connected, lastUpdate, incidentCount = 0, theme, onToggleTheme, onRefresh, onClear, onProfileClick }) {
  const [secondsAgo, setSecondsAgo] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const searchRef = useRef(null);
  const [clock, setClock] = useState(new Date());

  useEffect(() => {
    if(!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await api.globalSearch(searchQuery.trim(), 5);
        setSearchResults(res.results || []);
      } catch(e) {
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

  useEffect(() => {
    if (!lastUpdate) return;
    const tick = () => setSecondsAgo(Math.floor((Date.now() - new Date(lastUpdate).getTime()) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [lastUpdate]);

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const stalenessColor = secondsAgo < 10 ? 'text-green-400' : secondsAgo < 30 ? 'text-yellow-400' : 'text-red-400';

  return (
    <header className="sticky top-0 z-40 h-12 flex items-center justify-between px-6 border-b border-white/[0.05] bg-base-900/80 backdrop-blur-xl">
      {/* Left side */}
      <div className="flex items-center gap-4">
        {/* Live status */}
        <div className={cn('flex items-center gap-1.5', stalenessColor)}>
          <div className={cn(
            'w-[7px] h-[7px] rounded-full flex-shrink-0',
            connected ? 'bg-green-500 shadow-[0_0_6px_rgba(95,140,110,0.6)] animate-pulse-glow' : 'bg-red-500'
          )} />
          <span className="text-[10px] font-mono font-semibold tracking-wider uppercase">
            {connected ? 'Live' : 'Offline'}
          </span>
          {lastUpdate && (
            <span className="text-[10px] font-mono text-base-500 ml-1">
              {secondsAgo < 5 ? 'now' : `${secondsAgo}s`}
            </span>
          )}
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative flex items-center">
          <Search className="absolute left-2.5 w-3.5 h-3.5 text-base-500 pointer-events-none" />
          <input
            ref={searchRef}
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="h-7 w-44 rounded-full bg-white/[0.03] border border-white/[0.05] pl-8 pr-12 text-xs text-base-200 placeholder:text-base-500 outline-none focus:border-accent focus:bg-accent/[0.03] transition-all"
          />
          <kbd className="absolute right-2 text-[9px] font-mono text-base-500 bg-white/[0.04] px-1 py-0.5 rounded border border-white/[0.05]">
            {navigator.platform?.includes('Mac') ? '\u2318' : 'Ctrl'}K
          </kbd>

          {/* Search Dropdown */}
          {(searchQuery.trim() !== '' && searchResults !== null) && (
            <div className="absolute top-10 left-0 w-80 max-h-96 overflow-y-auto bg-base-900 border border-white/[0.1] rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.5)] z-50 p-2 flex flex-col gap-1 backdrop-blur-xl">
              {isSearching ? (
                 <div className="p-4 flex items-center justify-center text-xs text-base-500 gap-2">
                   <Loader2 className="w-4 h-4 animate-spin text-accent" /> Searching...
                 </div>
              ) : searchResults.length > 0 ? (
                 searchResults.map((res, idx) => (
                   <div key={res.event_id || res.incident_id || idx} className="p-2 rounded-lg hover:bg-white/[0.03] cursor-pointer transition-colors" onClick={() => { setSearchQuery(''); setSearchResults(null); }}>
                     <div className="text-[11px] font-semibold text-base-200 tracking-wide">{res.title || res.scenario_label || res.event_type || 'Unknown Event'}</div>
                     <div className="text-[10px] text-base-500 truncate mt-0.5">
                       {res.source_ip ? `IP: ${res.source_ip}` : (res.severity?.level ? `Severity: ${res.severity.level}` : res.source_layer || 'Event data')}
                     </div>
                   </div>
                 ))
              ) : (
                 <div className="p-4 text-center text-xs text-base-500">No matching events found.</div>
              )}
            </div>
          )}
        </div>

        <div className="w-px h-5 bg-white/[0.07]" />

        {/* Alerts */}
        <Button variant="icon" size="icon" title="Alerts" className="relative">
          <Bell className="w-3.5 h-3.5" />
          {incidentCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-red-500 rounded-full border border-base-900" />
          )}
        </Button>

        {/* Theme toggle */}
        <Button variant="icon" size="icon" onClick={onToggleTheme} title="Toggle theme">
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </Button>

        {/* Refresh */}
        <Button variant="icon" size="icon" onClick={onRefresh} title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>

        {/* Clear */}
        <Button variant="icon" size="icon" onClick={onClear} title="Clear data" className="text-red-400/50 hover:text-red-400">
          <Trash2 className="w-3.5 h-3.5" />
        </Button>

        <div className="w-px h-5 bg-white/[0.07]" />

        {/* Clock */}
        <span className="text-[10px] font-mono text-base-500 tabular-nums w-16 text-right">
          {clock.toLocaleTimeString()}
        </span>

        {/* Avatar */}
        <div 
          className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-blue-700 flex items-center justify-center text-[11px] font-bold text-white cursor-pointer hover:ring-2 hover:ring-accent/30 transition-all"
          onClick={onProfileClick}
        >
          A
        </div>
      </div>
    </header>
  );
}
