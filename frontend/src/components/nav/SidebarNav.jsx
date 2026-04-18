import { cn } from '@/lib/utils';
import { LogOut, Shield } from 'lucide-react';
import { NAV_ITEMS } from '@/components/nav/navConfig';

/**
 * Fixed ~130px left rail — discoverable primary nav (SOC flow).
 */
export default function SidebarNav({ activeTab, onTabChange, badges = {} }) {
  return (
    <aside
      className={cn(
        'flex w-[130px] shrink-0 flex-col self-stretch',
        'min-h-[calc(100vh-3rem)] border-r border-dashed border-white/[0.08] bg-base-900/95 backdrop-blur-sm'
      )}
    >
      <div className="flex min-h-[52px] items-center gap-2 border-b border-dashed border-white/[0.06] px-3 py-2.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-accent/20 bg-accent/[0.06]">
          <Shield className="h-4 w-4 text-accent" />
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-2 py-3" aria-label="Primary">
        {NAV_ITEMS.map(({ id, label, icon: Icon, badgeKey }) => {
          const count = badgeKey ? badges[badgeKey] : 0;
          const active = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onTabChange(id)}
              title={label}
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-[11px] font-medium leading-tight transition-colors',
                'border-l-[2px] border-transparent',
                active
                  ? 'border-l-accent bg-accent/[0.1] font-bold text-accent'
                  : 'text-base-400 hover:bg-white/[0.03] hover:text-base-200'
              )}
            >
              <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden />
              <span className="min-w-0 flex-1 truncate">{label}</span>
              {count > 0 && (
                <span className="shrink-0 rounded bg-red-500/90 px-1 font-mono text-[9px] font-bold text-white">
                  {count > 99 ? '99+' : count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-dashed border-white/[0.06] p-2">
        <button
          type="button"
          onClick={() => {
            try {
              localStorage.removeItem('securisphere_token');
              sessionStorage.removeItem('securisphere_token');
            } catch {
              /* ignore */
            }
            window.location.reload();
          }}
          className="flex w-full items-center justify-center gap-1 rounded-md py-2 text-[10px] font-medium text-base-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
          title="Sign out"
        >
          <LogOut className="h-3.5 w-3.5" />
          Out
        </button>
      </div>
    </aside>
  );
}
