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
//   User,
//   Command,
// } from 'lucide-react';
// import { cn } from '@/lib/utils';
// import { NAV_ITEMS } from './navConfig';

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

// /**
//  * @param {{
//  *   activeTab: string;
//  *   badges?: Record<string, number>;
//  *   connected?: boolean;
//  *   onProfileClick?: () => void;
//  *   onOpenCommandPalette?: () => void;
//  * }} props
//  */
// export default function TopNav({
//   activeTab: _activeTab,
//   badges = {},
//   connected = false,
//   onProfileClick,
//   onOpenCommandPalette,
// }) {
//   return (
//     <header className="flex h-[52px] shrink-0 items-center gap-2 border-b border-dashed border-base-800 bg-base-900/90 px-3 backdrop-blur-xl transition-colors duration-200">
//       <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
//         {NAV_ITEMS.map((item) => {
//           const Icon = ICONS[item.id] ?? LayoutDashboard;
//           const badge = badges[item.id];
//           return (
//             <NavLink
//               key={item.id}
//               to={item.path}
//               className={({ isActive }) =>
//                 cn(
//                   'flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1.5 font-mono text-[11px] transition-colors',
//                   isActive
//                     ? 'border-accent/35 bg-accent/10 text-accent'
//                     : 'border-transparent text-base-500 hover:border-base-800 hover:bg-base-950/50 hover:text-base-300'
//                 )
//               }
//               end={item.path === '/intro'}
//             >
//               <Icon className="h-3.5 w-3.5" />
//               <span className="hidden sm:inline">{item.label}</span>
//               {typeof badge === 'number' && badge > 0 && (
//                 <span className="rounded bg-base-800 px-1 text-[9px] text-base-400">{badge > 99 ? '99+' : badge}</span>
//               )}
//             </NavLink>
//           );
//         })}
//       </div>

//       <div className="flex shrink-0 items-center gap-2">
//         <button
//           type="button"
//           onClick={onOpenCommandPalette}
//           className="flex items-center gap-1 rounded border border-base-800 bg-base-950/50 px-2 py-1.5 font-mono text-[10px] text-base-500 transition-colors duration-200 hover:border-accent/30 hover:text-base-300"
//           title="Command palette (⌘K)"
//         >
//           <Command className="h-3.5 w-3.5" />
//           <span className="hidden sm:inline">⌘K</span>
//         </button>

//         <div
//           className={cn(
//             'flex items-center gap-1 font-mono text-[9px] font-semibold uppercase',
//             connected ? 'text-base-400' : 'text-base-600'
//           )}
//         >
//           <span
//             className={cn(
//               'h-1.5 w-1.5 rounded-full',
//               connected
//                 ? 'bg-base-400 shadow-[0_0_6px_rgba(0,0,0,0.1)] dark:shadow-[0_0_8px_rgba(255,255,255,0.08)]'
//                 : 'bg-base-600'
//             )}
//           />
//           <span className="hidden sm:inline">{connected ? 'live' : 'off'}</span>
//         </div>

//         <button
//           type="button"
//           onClick={onProfileClick}
//           className="rounded-md border border-base-800 p-1.5 text-base-400 transition-colors duration-200 hover:border-accent/30 hover:text-accent"
//           title="System"
//         >
//           <User className="h-4 w-4" />
//         </button>
//       </div>
//     </header>
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
  User,
  Command,
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

export default function TopNav({
  badges = {},
  connected = false,
  onProfileClick,
  onOpenCommandPalette,
}) {
  return (
    <header className="flex h-[56px] items-center justify-between border-b border-base-800 bg-base-900/80 px-4 backdrop-blur">

      {/* LEFT: NAVIGATION */}
      <nav className="flex items-center gap-4 overflow-x-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.id] ?? LayoutDashboard;
          const badge = badges[item.id];

          return (
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/intro'}
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
