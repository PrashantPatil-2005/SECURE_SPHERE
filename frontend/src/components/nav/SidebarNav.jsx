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
  Target,
  FlaskConical,
  RotateCcw,
  ScrollText,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { navItemsForRole } from './navConfig';
import { useAuth } from '@/contexts/AuthProvider';
import { useLocalStorage } from '@/hooks/useLocalStorage';

const ICONS = {
  dashboard:  LayoutDashboard,
  events:     Activity,
  incidents:  AlertTriangle,
  campaigns:  Target,
  evaluation: FlaskConical,
  topology:   Network,
  risk:       Gauge,
  mitre:      Shield,
  replay:     RotateCcw,
  audit:      ScrollText,
  users:      Users,
  system:     Server,
  settings:   Settings,
};

const SECTION_LABELS = {
  core:     null,
  analysis: 'Analysis',
  infra:    'Infrastructure',
  security: 'Security',
  system:   'System',
};

const COLLAPSED_KEY = 'securisphere-sidebar-collapsed';

function groupBySection(items) {
  const groups = [];
  let last = null;
  for (const item of items) {
    if (item.section !== last) {
      last = item.section;
      groups.push({ section: item.section, items: [] });
    }
    groups[groups.length - 1].items.push(item);
  }
  return groups;
}

export default function SidebarNav({ badges = {} }) {
  const { role, user } = useAuth();
  const navItems = navItemsForRole(role);
  const [collapsed, setCollapsed] = useLocalStorage(COLLAPSED_KEY, false);

  const groups = groupBySection(navItems);
  const userInitial = (user?.username?.[0] || user?.email?.[0] || 'U').toUpperCase();
  const userName = user?.username || user?.email || 'User';
  const userRole = (user?.role || role || 'viewer').toLowerCase();

  return (
    <aside
      className={cn(
        'relative flex h-screen flex-col border-r border-base-800 bg-base-950',
        'transition-all duration-300 ease-out',
        collapsed ? 'w-[60px]' : 'w-[200px]'
      )}
    >
      {/* ── Logo ──────────────────────────────────────────────────────── */}
      <div
        className={cn(
          'flex items-center border-b border-base-800',
          collapsed ? 'justify-center px-2 py-3' : 'justify-between px-3.5 py-[14px]'
        )}
      >
        <div className={cn('flex items-center', collapsed ? 'gap-0' : 'gap-2.5')}>
          <div
            className="flex h-[30px] w-[30px] items-center justify-center rounded-lg border shrink-0"
            style={{
              borderColor: 'var(--sev-critical-border)',
              background: 'linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05))',
            }}
          >
            <Hexagon className="h-3.5 w-3.5" style={{ color: 'var(--sev-critical)' }} />
          </div>
          {!collapsed && (
            <div className="leading-tight min-w-0">
              <div className="text-sm font-bold tracking-tight text-base-100">SecuriSphere</div>
              <div className="type-eyebrow font-mono text-base-600">v2.0 · SOC</div>
            </div>
          )}
        </div>

        {!collapsed && (
          <button
            onClick={() => setCollapsed(true)}
            aria-label="Collapse sidebar"
            className="flex h-6 w-6 items-center justify-center rounded-md border border-base-800 bg-base-900 text-base-500 transition-all hover:border-base-700 hover:text-base-200 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          aria-label="Expand sidebar"
          className="mx-auto mt-2 flex h-6 w-6 items-center justify-center rounded-md border border-base-800 bg-base-900 text-base-500 transition-all hover:border-base-700 hover:text-base-200"
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      )}

      {/* ── Nav ───────────────────────────────────────────────────────── */}
      <nav
        aria-label="Primary"
        className={cn(
          'flex flex-1 flex-col overflow-y-auto',
          collapsed ? 'px-1.5 py-2' : 'px-2 py-2'
        )}
      >
        {groups.map(({ section, items }, gi) => (
          <div key={section}>
            {/* Section separator */}
            {gi > 0 && (
              <div className={cn('mx-1 my-1.5', collapsed ? '' : '')}>
                {collapsed ? (
                  <div className="h-px bg-base-800" />
                ) : (
                  <div className="flex items-center gap-2 px-1 py-0.5">
                    <div className="h-px flex-1 bg-base-800" />
                    {SECTION_LABELS[section] && (
                      <span className="type-eyebrow font-mono text-base-600 select-none">
                        {SECTION_LABELS[section]}
                      </span>
                    )}
                    <div className="h-px flex-1 bg-base-800" />
                  </div>
                )}
              </div>
            )}

            {/* Items */}
            <div className="flex flex-col gap-0.5">
              {items.map((item) => {
                const Icon = ICONS[item.id] ?? LayoutDashboard;
                const badge = badges[item.id];
                const isCriticalBadge = item.id === 'incidents' && typeof badge === 'number' && badge > 0;

                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    end={item.path === '/dashboard'}
                    title={collapsed ? item.label : undefined}
                    className="relative block rounded-[8px] focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
                  >
                    {({ isActive }) => (
                      <>
                        {/* Left accent bar */}
                        {isActive && (
                          <span className="pointer-events-none absolute inset-y-1.5 left-0 w-[3px] rounded-r-full bg-accent" />
                        )}

                        <div
                          className={cn(
                            'flex items-center rounded-[8px] text-xs transition-all duration-150',
                            collapsed ? 'justify-center p-2.5' : 'gap-2.5 px-2.5 py-2',
                            isActive
                              ? 'bg-accent/[0.09] font-semibold text-base-100'
                              : 'font-medium text-base-500 hover:bg-white/[0.04] hover:text-base-300'
                          )}
                        >
                          <Icon
                            className={cn(
                              'h-[15px] w-[15px] shrink-0 transition-colors',
                              isActive ? 'text-accent' : ''
                            )}
                          />

                          {!collapsed && (
                            <span className="flex-1 truncate">{item.label}</span>
                          )}

                          {/* Badges — expanded */}
                          {!collapsed && isCriticalBadge && (
                            <span
                              className="rounded-full px-1.5 text-2xs font-bold leading-none"
                              style={{
                                background: 'var(--sev-critical-bg)',
                                border: '1px solid var(--sev-critical-border)',
                                color: 'var(--sev-critical)',
                              }}
                            >
                              {badge > 99 ? '99+' : badge}
                            </span>
                          )}

                          {!collapsed && !isCriticalBadge && typeof badge === 'number' && badge > 0 && (
                            <span className="type-data rounded bg-base-800 px-1.5 text-2xs text-base-400">
                              {badge > 99 ? '99+' : badge}
                            </span>
                          )}

                          {/* Badges — collapsed */}
                          {collapsed && typeof badge === 'number' && badge > 0 && (
                            <span
                              className={cn('absolute right-0.5 top-0.5 min-w-[14px] rounded-full px-0.5 text-center text-[8px] font-bold leading-[14px]')}
                              style={
                                isCriticalBadge
                                  ? {
                                      background: 'var(--sev-critical)',
                                      color: '#fff',
                                    }
                                  : { background: 'var(--base-700)', color: 'var(--base-300)' }
                              }
                            >
                              {badge > 9 ? '9+' : badge}
                            </span>
                          )}

                          {/* Collapsed tooltip */}
                          {collapsed && (
                            <span className="pointer-events-none absolute left-full z-50 ml-2.5 whitespace-nowrap rounded-lg border border-base-800 bg-base-900 px-2.5 py-1.5 text-xs text-base-200 opacity-0 shadow-xl transition-opacity group-hover:opacity-100 [.group:hover_&]:opacity-100">
                              {item.label}
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* ── User footer ───────────────────────────────────────────────── */}
      {!collapsed && (
        <div className="border-t border-base-800 px-2.5 py-2.5">
          <div className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/[0.03]">
            <div
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
              style={{ background: 'linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 50%, transparent))' }}
            >
              {userInitial}
            </div>
            <div className="min-w-0 leading-tight">
              <div className="truncate text-xs font-semibold text-base-300">{userName}</div>
              <div className="type-eyebrow text-base-600">{userRole}</div>
            </div>
          </div>
        </div>
      )}

      {collapsed && (
        <div className="border-t border-base-800 px-1.5 py-2">
          <div
            className="mx-auto flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white"
            style={{ background: 'linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 50%, transparent))' }}
            title={`${userName} (${userRole})`}
          >
            {userInitial}
          </div>
        </div>
      )}
    </aside>
  );
}
