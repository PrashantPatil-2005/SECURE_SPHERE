import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  AlertTriangle,
  Network,
  Gauge,
  Shield,
  Server,
  Users,
  ChevronLeft,
  ChevronRight,
  Hexagon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { navItemsForRole } from './navConfig';
import { useAuth } from '@/contexts/AuthProvider';
import { useLocalStorage } from '@/hooks/useLocalStorage';

const ICONS = {
  dashboard: LayoutDashboard,
  events: Activity,
  incidents: AlertTriangle,
  topology: Network,
  risk: Gauge,
  mitre: Shield,
  users: Users,
  system: Server,
};

const COLLAPSED_KEY = 'securisphere-sidebar-collapsed';

export default function SidebarNav({ badges = {} }) {
  const { role } = useAuth();
  const navItems = navItemsForRole(role);
  const [collapsed, setCollapsed] = useLocalStorage(COLLAPSED_KEY, false);

  return (
    <aside
      className={cn(
        'relative flex h-screen flex-col border-r border-base-800 bg-base-950',
        'transition-all duration-300 ease-out',
        collapsed ? 'w-[60px]' : 'w-[200px]'
      )}
    >
      {/* Logo block */}
      <div
        className={cn(
          'flex items-center border-b border-base-800',
          collapsed ? 'justify-center px-2 py-3' : 'justify-between px-4 py-[14px]'
        )}
      >
        <div className={cn('flex items-center', collapsed ? 'gap-0' : 'gap-2.5')}>
          <div
            className="flex h-[30px] w-[30px] items-center justify-center rounded-lg border text-sev-critical"
            style={{
              borderColor: 'var(--sev-critical-border)',
              background:
                'linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05))',
            }}
          >
            <Hexagon className="h-3.5 w-3.5" />
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="text-[13px] font-bold tracking-tight text-base-100">
                SecuriSphere
              </div>
              <div className="font-mono text-[9px] uppercase tracking-[0.08em] text-base-600">
                v2.0 · SOC
              </div>
            </div>
          )}
        </div>

        {!collapsed && (
          <button
            onClick={() => setCollapsed((c) => !c)}
            aria-label="Collapse sidebar"
            aria-expanded
            className="flex h-6 w-6 items-center justify-center rounded-md border border-base-800 bg-base-950 text-base-500 transition-all hover:border-base-700 hover:text-base-200 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          aria-label="Expand sidebar"
          className="mx-auto mt-2 flex h-6 w-6 items-center justify-center rounded-md border border-base-800 bg-base-950 text-base-500 transition-all hover:border-base-700 hover:text-base-200"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Nav */}
      <nav
        aria-label="Primary"
        className={cn('flex flex-1 flex-col gap-0.5 overflow-y-auto', collapsed ? 'px-1.5 py-2' : 'px-2 py-2')}
      >
        {!collapsed && (
          <div className="mb-1.5 px-2 font-mono text-[9px] font-bold uppercase tracking-[0.1em] text-base-600">
            Navigation
          </div>
        )}
        {navItems.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];
          const showSevBadge = item.id === 'incidents' && typeof badge === 'number' && badge > 0;

          return (
            <NavLink
              key={item.id}
              to={item.path}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center rounded-lg text-[12px] transition-all duration-150',
                  'focus:outline-none focus-visible:ring-1 focus-visible:ring-accent',
                  collapsed ? 'justify-center px-0 py-2.5' : 'gap-2.5 px-2.5 py-[7px]',
                  isActive
                    ? 'bg-white/[0.06] font-semibold text-base-100 shadow-[inset_0_0_0_1px_rgba(250,250,250,0.08),0_0_18px_-4px_rgba(250,250,250,0.1)]'
                    : 'text-base-500 hover:bg-white/[0.03] hover:text-base-300'
                )
              }
            >
              <Icon className="h-[15px] w-[15px] shrink-0" />

              {!collapsed && (
                <span className="flex-1 truncate">{item.label}</span>
              )}

              {!collapsed && showSevBadge && (
                <span
                  className="rounded-full px-1.5 text-[9px] font-bold"
                  style={{
                    background: 'var(--sev-critical-bg)',
                    border: `1px solid var(--sev-critical-border)`,
                    color: 'var(--sev-critical)',
                  }}
                >
                  {badge > 99 ? '99+' : badge}
                </span>
              )}

              {!collapsed && !showSevBadge && typeof badge === 'number' && badge > 0 && (
                <span className="rounded bg-base-800 px-1.5 text-[10px] text-base-300">
                  {badge > 99 ? '99+' : badge}
                </span>
              )}

              {collapsed && typeof badge === 'number' && badge > 0 && (
                <span
                  className={cn(
                    'absolute right-1 top-1 rounded-full px-1 text-[9px] font-bold',
                    showSevBadge ? '' : 'bg-base-800 text-base-300'
                  )}
                  style={
                    showSevBadge
                      ? {
                          background: 'var(--sev-critical-bg)',
                          border: '1px solid var(--sev-critical-border)',
                          color: 'var(--sev-critical)',
                        }
                      : undefined
                  }
                >
                  {badge > 99 ? '99+' : badge}
                </span>
              )}

              {collapsed && (
                <span className="pointer-events-none absolute left-full z-50 ml-2 whitespace-nowrap rounded-md border border-base-800 bg-base-950 px-2 py-1 text-xs text-base-200 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                  {item.label}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Analyst footer */}
      {!collapsed && (
        <div className="border-t border-base-800 px-3 py-2.5">
          <div className="flex items-center gap-2 rounded-lg bg-white/[0.03] px-2 py-1.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-base-800 text-[10px] font-bold text-base-400">
              A
            </div>
            <div className="leading-tight">
              <div className="text-[11px] font-semibold text-base-300">Analyst</div>
              <div className="text-[9px] text-base-600">SOC Tier 2</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}