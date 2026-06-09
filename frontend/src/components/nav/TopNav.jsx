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
  User,
  Command,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { navItemsForRole } from './navConfig';
import { useAuth } from '@/contexts/AuthProvider';

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

export default function TopNav({
  badges = {},
  connected = false,
  onProfileClick,
  onOpenCommandPalette,
}) {
  const { role } = useAuth();
  const navItems = navItemsForRole(role);

  return (
    <header className="flex h-[56px] items-center justify-between border-b border-base-800 bg-base-900/80 px-4 backdrop-blur">

      {/* LEFT: NAVIGATION */}
      <nav aria-label="Primary" className="flex items-center gap-4 overflow-x-auto">
        {navItems.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];

          return (
            <NavLink
              key={item.id}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'relative flex items-center gap-2 px-2 py-1.5 text-sm transition-colors',
                  isActive
                    ? 'text-accent'
                    : 'text-base-500 hover:text-base-200'
                )
              }
            >
              <Icon className="h-4 w-4" />

              <span className="hidden sm:inline">
                {item.label}
              </span>

              {typeof badge === 'number' && badge > 0 && (
                <span className="rounded bg-base-800 px-1.5 text-[10px] text-base-300">
                  {badge > 99 ? '99+' : badge}
                </span>
              )}

              {/* ACTIVE INDICATOR (clean + strong) */}
              <span className="absolute bottom-[-8px] left-0 h-[2px] w-full bg-accent opacity-0 transition-all group-data-[active=true]:opacity-100" />
            </NavLink>
          );
        })}
      </nav>

      {/* RIGHT: ACTIONS */}
      <div className="flex items-center gap-3">

        {/* Command */}
        <button
          onClick={onOpenCommandPalette}
          className="group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-base-500 transition hover:bg-base-800 hover:text-base-200"
        >
          <Command className="h-4 w-4 transition-colors group-hover:text-accent" />
          <kbd className="hidden items-center gap-0.5 rounded border border-base-700 bg-base-800/50 px-1.5 py-0.5 font-mono text-[10px] font-medium text-base-300 shadow-sm transition-colors group-hover:border-accent/40 group-hover:text-base-100 sm:inline-flex">
            <span className="text-[11px] opacity-70"></span>
            <span></span>
          </kbd>
        </button>

        {/* Status */}
        <div className="flex items-center gap-1.5 text-xs text-base-500">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              connected ? 'bg-green-500' : 'bg-base-600'
            )}
          />
          <span className="hidden sm:inline">
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>

        {/* Profile */}
        <button
          onClick={onProfileClick}
          className="rounded-md p-2 text-base-400 transition hover:bg-base-800 hover:text-base-100"
        >
          <User className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
