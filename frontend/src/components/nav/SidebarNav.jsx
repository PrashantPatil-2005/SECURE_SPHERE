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
        'relative flex h-screen flex-col border-r border-base-800 bg-base-900/70 backdrop-blur',
        'transition-all duration-300 ease-out',
        collapsed ? 'w-[60px]' : 'w-[220px]'
      )}
    >
      {/* Header */}
      <div
        className={cn(
          'flex items-center border-b border-base-800 px-3 py-3',
          collapsed ? 'justify-center' : 'justify-between'
        )}
      >
        {!collapsed && (
          <div className="flex flex-col leading-tight">
            <span className="font-mono text-xs font-semibold tracking-wide text-base-200">
              SecuriSphere
            </span>
            <span className="text-[10px] text-base-500">Security Ops</span>
          </div>
        )}

        <button
          onClick={() => setCollapsed((c) => !c)}
          aria-label="Toggle sidebar"
          className="flex h-7 w-7 items-center justify-center rounded-md border border-base-800 bg-base-950 text-base-400 transition-all hover:border-base-600 hover:text-white focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-1 px-2 py-3">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];

          return (
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/intro'}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center rounded-md text-sm transition-all duration-200',
                  'focus:outline-none focus-visible:ring-1 focus-visible:ring-accent',
                  collapsed ? 'justify-center px-0 py-3' : 'gap-3 px-3 py-2',
                  isActive
                    ? 'bg-accent/10 text-accent'
                    : 'text-base-400 hover:bg-base-800 hover:text-base-100'
                )
              }
            >
              {/* Icon */}
              <Icon className="h-4 w-4 shrink-0" />

              {/* Label */}
              {!collapsed && (
                <span className="flex-1 truncate">{item.label}</span>
              )}

              {/* Badge */}
              {typeof badge === 'number' && badge > 0 && (
                <span
                  className={cn(
                    'rounded bg-base-800 px-1.5 text-[10px] text-base-300',
                    collapsed
                      ? 'absolute right-1 top-1 text-[9px]'
                      : ''
                  )}
                >
                  {badge > 99 ? '99+' : badge}
                </span>
              )}

              {/* Tooltip (collapsed mode) */}
              {collapsed && (
                <span className="pointer-events-none absolute left-full z-50 ml-2 whitespace-nowrap rounded-md bg-black px-2 py-1 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                  {item.label}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}