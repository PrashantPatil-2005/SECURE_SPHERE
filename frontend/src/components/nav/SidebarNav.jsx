import { NavLink } from 'react-router-dom';
import {
  BookOpen,
  LayoutDashboard,
  Activity,
  AlertTriangle,
  Network,
  Gauge,
  Shield,
  Server,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from './navConfig';

const ICONS = {
  intro: BookOpen,
  dashboard: LayoutDashboard,
  events: Activity,
  incidents: AlertTriangle,
  topology: Network,
  risk: Gauge,
  mitre: Shield,
  system: Server,
};

/**
 * @param {{ badges?: Record<string, number> }} props
 */
export default function SidebarNav({ badges = {} }) {
  return (
    <aside className="flex w-[130px] shrink-0 flex-col border-r border-dashed border-base-800 bg-base-900/80 transition-colors duration-200">
      <div className="border-b border-dashed border-base-800 px-2 py-2">
        <span className="font-mono text-[9px] font-semibold uppercase tracking-wider text-base-600">
          SecuriSphere
        </span>
      </div>
      <nav className="flex flex-col gap-0.5 p-1.5" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];
          return (
            <NavLink
              key={item.id}
              to={item.path}
              title={item.label}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-1.5 rounded-md px-1.5 py-1.5 font-mono text-[10px] transition-colors',
                  isActive
                    ? 'bg-accent/15 text-accent'
                    : 'text-base-500 hover:bg-base-950/40 hover:text-base-300'
                )
              }
              end={item.path === '/intro'}
            >
              <Icon className="h-3.5 w-3.5 shrink-0 opacity-90" />
              <span className="min-w-0 flex-1 truncate leading-tight">{item.label}</span>
              {typeof badge === 'number' && badge > 0 && (
                <span className="shrink-0 rounded bg-base-800 px-1 font-mono text-[9px] text-base-400">
                  {badge > 99 ? '99+' : badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
