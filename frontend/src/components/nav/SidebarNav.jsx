// import { NavLink } from 'react-router-dom';
// import {
//   BookOpen,
//   LayoutDashboard,
//   Activity,
//   AlertTriangle,
//   Network,
//   Gauge,
//   Shield,
//   Server,
//   ChevronLeft,
//   ChevronRight,
// } from 'lucide-react';
// import { cn } from '@/lib/utils';
// import { NAV_ITEMS } from './navConfig';
// import { useLocalStorage } from '@/hooks/useLocalStorage';

// const ICONS = {
//   intro: BookOpen,
//   dashboard: LayoutDashboard,
//   events: Activity,
//   incidents: AlertTriangle,
//   topology: Network,
//   risk: Gauge,
//   mitre: Shield,
//   system: Server,
// };

// const COLLAPSED_KEY = 'securisphere-sidebar-collapsed';

// /**
//  * Collapsible sidebar — animates width + label slide between expanded and
//  * icon-only rails. State persists in localStorage.
//  *
//  * @param {{ badges?: Record<string, number> }} props
//  */
// export default function SidebarNav({ badges = {} }) {
//   const [collapsed, setCollapsed] = useLocalStorage(COLLAPSED_KEY, false);

//   return (
//     <aside
//       className={cn(
//         'relative flex shrink-0 flex-col border-r border-dashed border-base-800 bg-base-900/80',
//         'transition-[width,background-color,border-color] duration-300 ease-out',
//         collapsed ? 'w-[52px]' : 'w-[130px]'
//       )}
//       data-collapsed={collapsed ? 'true' : 'false'}
//     >
//       <div
//         className={cn(
//           'flex items-center border-b border-dashed border-base-800 py-2',
//           collapsed ? 'justify-center px-0' : 'justify-between px-2'
//         )}
//       >
//         <span
//           className={cn(
//             'overflow-hidden whitespace-nowrap font-mono text-[9px] font-semibold uppercase tracking-wider text-base-600',
//             'transition-[max-width,opacity] duration-300 ease-out',
//             collapsed ? 'max-w-0 opacity-0' : 'max-w-[90px] opacity-100'
//           )}
//         >
//           SecuriSphere
//         </span>
//         <button
//           type="button"
//           onClick={() => setCollapsed((c) => !c)}
//           title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
//           aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
//           aria-expanded={!collapsed}
//           className="flex h-5 w-5 shrink-0 items-center justify-center rounded border border-base-800 bg-base-950/60 text-base-500 transition-colors hover:border-accent/35 hover:text-accent"
//         >
//           {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
//         </button>
//       </div>

//       <nav className="flex flex-col gap-0.5 p-1.5" aria-label="Primary">
//         {NAV_ITEMS.map((item) => {
//           const Icon = ICONS[item.id] ?? LayoutDashboard;
//           const badge = badges[item.id];
//           return (
//             <NavLink
//               key={item.id}
//               to={item.path}
//               title={item.label}
//               className={({ isActive }) =>
//                 cn(
//                   'group relative flex items-center gap-1.5 rounded-md py-1.5 font-mono text-[10px] transition-colors duration-200',
//                   collapsed ? 'justify-center px-0' : 'px-1.5',
//                   isActive
//                     ? 'bg-accent/15 text-accent'
//                     : 'text-base-500 hover:bg-base-950/40 hover:text-base-300'
//                 )
//               }
//               end={item.path === '/intro'}
//             >
//               <Icon className="h-3.5 w-3.5 shrink-0 opacity-90" />
//               <span
//                 className={cn(
//                   'min-w-0 overflow-hidden whitespace-nowrap leading-tight',
//                   'transition-[max-width,opacity,margin] duration-300 ease-out',
//                   collapsed ? 'max-w-0 opacity-0' : 'max-w-[90px] flex-1 opacity-100'
//                 )}
//               >
//                 {item.label}
//               </span>
//               {typeof badge === 'number' && badge > 0 && (
//                 <span
//                   className={cn(
//                     'shrink-0 rounded bg-base-800 px-1 font-mono text-[9px] text-base-400',
//                     collapsed &&
//                       'absolute right-0 top-0 -translate-y-1/2 translate-x-1/3 border border-base-900 bg-accent/80 text-base-950'
//                   )}
//                 >
//                   {badge > 99 ? '99+' : badge}
//                 </span>
//               )}
//             </NavLink>
//           );
//         })}
//       </nav>
//     </aside>
//   );
// }

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
  ChevronLeft,
  ChevronRight,
  Hexagon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from './navConfig';
import { useLocalStorage } from '@/hooks/useLocalStorage';

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

const COLLAPSED_KEY = 'securisphere-sidebar-collapsed';

export default function SidebarNav({ badges = {} }) {
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
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];
          const showSevBadge = item.id === 'incidents' && typeof badge === 'number' && badge > 0;

          return (
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/intro'}
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