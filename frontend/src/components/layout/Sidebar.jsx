import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard, Radio, Network, AlertTriangle,
  Zap, Server, ChevronRight, LogOut, Shield, Pin,
} from 'lucide-react';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'events', label: 'Events', icon: Radio, badgeKey: 'events' },
  { id: 'incidents', label: 'Kill Chains', icon: AlertTriangle, badgeKey: 'incidents' },
  { id: 'topology', label: 'Topology', icon: Network },
  { id: 'risk', label: 'Risk Scores', icon: Zap },
  { id: 'system', label: 'System', icon: Server },
];

export default function Sidebar({ activeTab, onTabChange, badges = {}, connected }) {
  const [pinned, setPinned] = useState(() => {
    try { return localStorage.getItem('ss_sidebar_pinned') === 'true'; } catch { return false; }
  });
  const [hovered, setHovered] = useState(false);
  const open = pinned || hovered;

  useEffect(() => {
    try { localStorage.setItem('ss_sidebar_pinned', pinned); } catch {}
  }, [pinned]);

  return (
    <aside
      className={cn(
        'fixed top-0 left-0 h-screen z-50 flex flex-col',
        'bg-base-900 dark:bg-base-900 border-r border-white/[0.05]',
        'transition-all duration-200 ease-out overflow-hidden',
        open ? 'w-[220px]' : 'w-16'
      )}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-3 min-h-[48px]">
        <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0">
          <Shield className="w-4 h-4 text-accent" />
        </div>
        <div className={cn('overflow-hidden whitespace-nowrap transition-all duration-200', open ? 'opacity-100 w-auto' : 'opacity-0 w-0')}>
          <div className="text-sm font-bold text-base-100 tracking-tight">SecuriSphere</div>
          <div className="text-[9px] text-base-500 uppercase tracking-widest">Threat Intel</div>
        </div>
      </div>

      <div className="h-px bg-white/[0.05] mx-3" />

      {/* Section label */}
      <div className={cn(
        'text-[9px] font-semibold text-base-500 uppercase tracking-[0.1em] transition-all',
        open ? 'opacity-100 px-5 pt-4 pb-2' : 'opacity-0 h-0 overflow-hidden'
      )}>
        Monitor
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col gap-0.5 px-2 py-1">
        {navItems.map(({ id, label, icon: Icon, badgeKey }) => {
          const count = badgeKey ? badges[badgeKey] : 0;
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              title={!open ? label : undefined}
              className={cn(
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                'border-l-[3px] border-transparent',
                active
                  ? 'text-accent bg-accent/[0.08] border-l-accent font-semibold'
                  : 'text-base-400 hover:text-base-200 hover:bg-white/[0.03]'
              )}
            >
              <Icon className="w-[18px] h-[18px] flex-shrink-0" />
              <span className={cn('transition-all duration-200 whitespace-nowrap', open ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden')}>
                {label}
              </span>
              {count > 0 && (
                <span className={cn(
                  'bg-red-500 text-white text-[10px] font-bold px-1.5 rounded-full min-w-[18px] text-center font-mono leading-[18px]',
                  open ? 'ml-auto' : 'absolute top-0.5 right-0.5'
                )}>
                  {count > 99 ? '99+' : count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Connection status */}
      <div className="px-4 py-2 flex items-center gap-2">
        <div className={cn(
          'w-[7px] h-[7px] rounded-full flex-shrink-0',
          connected ? 'bg-green-500 shadow-[0_0_6px_rgba(95,140,110,0.6)] animate-pulse-glow' : 'bg-base-500'
        )} />
        <span className={cn(
          'text-[10px] font-mono transition-all',
          open ? 'opacity-100' : 'opacity-0',
          connected ? 'text-green-400 font-semibold' : 'text-base-500'
        )}>
          {connected ? 'Connected' : 'Offline'}
        </span>
      </div>

      {/* Footer */}
      <div className="border-t border-white/[0.05] px-2 py-2 flex gap-1">
        <button
          onClick={() => setPinned(p => !p)}
          title={pinned ? 'Unpin sidebar' : 'Pin sidebar'}
          className="flex-1 flex items-center gap-2 px-2 py-1.5 rounded text-base-500 hover:text-base-300 hover:bg-white/[0.03] transition-all text-xs"
        >
          {pinned ? <Pin className="w-3.5 h-3.5 fill-current" /> : <ChevronRight className="w-3.5 h-3.5" style={{ transform: pinned ? 'rotate(180deg)' : undefined }} />}
          <span className={cn('transition-all', open ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden')}>
            {pinned ? 'Unpin' : 'Pin'}
          </span>
        </button>
        {open && (
          <button
            onClick={() => {
              localStorage.removeItem('securisphere_token');
              sessionStorage.removeItem('securisphere_token');
              window.location.reload();
            }}
            title="Sign out"
            className="px-2 py-1.5 rounded text-red-400/60 hover:text-red-400 hover:bg-red-500/10 transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </aside>
  );
}
