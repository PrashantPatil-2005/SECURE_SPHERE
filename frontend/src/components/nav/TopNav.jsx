import { cn } from '@/lib/utils';
import { Shield } from 'lucide-react';
import { useState, useEffect } from 'react';
import { NAV_ITEMS, pathForTab } from '@/components/nav/navConfig';

/**
 * Horizontal pill navigation — full-width content below.
 */
export default function TopNav({
  activeTab,
  onTabChange,
  badges = {},
  connected,
  onProfileClick,
  onOpenCommandPalette,
}) {
  const [email, setEmail] = useState('analyst@securisphere.local');
  useEffect(() => {
    try {
      const v = localStorage.getItem('ss_analyst_email');
      if (v) setEmail(v);
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <header
      className={cn(
        'sticky top-0 z-40 flex min-h-[52px] flex-wrap items-center gap-x-2 gap-y-2 border-b border-dashed border-white/[0.08]',
        'bg-base-900/90 px-4 py-2 backdrop-blur-xl'
      )}
    >
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-accent/20 bg-accent/[0.06]">
          <Shield className="h-4 w-4 text-accent" />
        </div>
        <span className="text-sm font-bold tracking-tight text-base-100">SecuriSphere</span>
        <span className="hidden font-mono text-[10px] text-base-600 sm:inline">
          {pathForTab(activeTab)}
        </span>
      </div>

      <nav className="flex flex-1 flex-wrap items-center gap-1" aria-label="Primary">
        {NAV_ITEMS.map(({ id, label, badgeKey }) => {
          const count = badgeKey ? badges[badgeKey] : 0;
          const active = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onTabChange(id)}
              className={cn(
                'rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors',
                active
                  ? 'border-accent/40 bg-accent/15 font-semibold text-accent'
                  : 'border-transparent font-mono text-base-500 hover:border-white/[0.06] hover:text-base-300'
              )}
            >
              {label.toLowerCase()}
              {count > 0 && (
                <span className="ml-1 font-mono text-[10px] text-red-400">({count > 99 ? '99+' : count})</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={onOpenCommandPalette}
          className="shrink-0 rounded border border-white/[0.08] bg-base-950/50 px-2 py-1 font-mono text-[10px] text-base-500 transition-colors hover:border-accent/30 hover:text-base-400"
          title="Command palette"
        >
          ⌘K
        </button>
        <div className="flex items-center gap-1.5 rounded-full border border-green-500/25 bg-green-500/[0.07] px-2 py-0.5">
          <span
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              connected ? 'bg-green-500 shadow-[0_0_6px_rgba(95,140,110,0.5)]' : 'bg-base-500'
            )}
          />
          <span className="font-mono text-[10px] font-semibold tracking-wide text-green-400/90">
            live
          </span>
        </div>
        <button
          type="button"
          onClick={onProfileClick}
          className="max-w-[140px] truncate font-mono text-[10px] text-base-400 transition-colors hover:text-base-200"
          title="System / profile"
        >
          {email}
        </button>
      </div>
    </header>
  );
}
