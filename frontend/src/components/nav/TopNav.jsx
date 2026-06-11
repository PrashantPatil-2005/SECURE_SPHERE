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
  Target,
  FlaskConical,
  RotateCcw,
  ScrollText,
  Settings,
  User,
  Command,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { navItemsForRole } from './navConfig';
import { useAuth } from '@/contexts/AuthProvider';

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

export default function TopNav({
  badges = {},
  connected = false,
  onProfileClick,
  onOpenCommandPalette,
}) {
  const { role } = useAuth();
  const navItems = navItemsForRole(role);

  return (
    <header className="flex h-12 items-center justify-between border-b border-base-800 bg-base-950/95 px-4 backdrop-blur-xl">

      {/* LEFT: navigation */}
      <nav aria-label="Primary" className="flex items-center gap-1 overflow-x-auto">
        {navItems.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];

          return (
            <NavLink
              key={item.id}
              to={item.path}
              className="relative"
            >
              {({ isActive }) => (
                <div
                  className={cn(
                    'relative flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors duration-150',
                    isActive
                      ? 'bg-accent/[0.09] font-semibold text-base-100'
                      : 'font-medium text-base-500 hover:bg-white/[0.03] hover:text-base-300'
                  )}
                >
                  <Icon className={cn('h-3.5 w-3.5 shrink-0', isActive && 'text-accent')} />
                  <span className="hidden sm:inline">{item.label}</span>

                  {typeof badge === 'number' && badge > 0 && (
                    <span className="type-data rounded bg-base-800 px-1 text-2xs font-bold text-base-300">
                      {badge > 99 ? '99+' : badge}
                    </span>
                  )}

                  {/* Active underline — rendered from isActive in render prop */}
                  {isActive && (
                    <span className="absolute bottom-[-8px] left-0 h-[2px] w-full rounded-full bg-accent" />
                  )}
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* RIGHT: actions */}
      <div className="flex items-center gap-2">

        {/* Command palette */}
        <button
          onClick={onOpenCommandPalette}
          className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-base-500 transition hover:bg-base-800 hover:text-base-200"
          title="Command palette (⌘K)"
        >
          <Command className="h-3.5 w-3.5 transition-colors group-hover:text-accent" />
          <kbd className="hidden items-center gap-0.5 rounded border border-base-700 bg-base-800/50 px-1.5 py-0.5 font-mono text-2xs font-medium text-base-300 shadow-sm transition-colors group-hover:border-accent/40 group-hover:text-base-100 sm:inline-flex">
            <span className="opacity-70">⌘</span>
            <span>K</span>
          </kbd>
        </button>

        {/* Connection status */}
        <div className="flex items-center gap-1.5 text-xs text-base-500">
          <span
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              connected ? 'bg-emerald-400' : 'bg-base-600'
            )}
          />
          <span className="hidden sm:inline">{connected ? 'Live' : 'Offline'}</span>
        </div>

        {/* Profile */}
        <button
          onClick={onProfileClick}
          className="rounded-md p-1.5 text-base-400 transition hover:bg-base-800 hover:text-base-100"
          aria-label="Profile"
        >
          <User className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
