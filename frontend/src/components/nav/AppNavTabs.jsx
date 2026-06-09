import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from './navConfig';

/**
 * Polished horizontal navigation tabs (production-ready).
 */
export default function AppNavTabs({ badges = {}, className }) {
  return (
    <div
      className={cn(
        'relative border-b border-base-800',
        className
      )}
    >
      {/* Scroll container */}
      <div className="flex gap-2 overflow-x-auto px-1 pb-2 scrollbar-none">
        {NAV_ITEMS.map((item) => {
          const badge = badges[item.id];

          return (
            <NavLink
              key={item.id}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-1.5 text-xs transition-all',
                  'focus:outline-none focus-visible:ring-1 focus-visible:ring-accent',
                  isActive
                    ? 'text-accent'
                    : 'text-base-500 hover:text-base-200'
                )
              }
            >
              {/* Label */}
              <span className="font-medium tracking-wide">
                {item.label}
              </span>

              {/* Badge */}
              {typeof badge === 'number' && badge > 0 && (
                <span
                  className={cn(
                    'rounded bg-base-800 px-1.5 py-[1px] text-[10px] text-base-300',
                    'group-hover:bg-base-700'
                  )}
                >
                  {badge > 99 ? '99+' : badge}
                </span>
              )}

              {/* Active underline */}
              <span
                className={cn(
                  'absolute bottom-0 left-0 h-[2px] w-full rounded-full transition-all duration-300',
                  'bg-accent',
                  'scale-x-0 group-data-[active=true]:scale-x-100'
                )}
              />
            </NavLink>
          );
        })}
      </div>

      {/* subtle fade edges (premium feel) */}
      <div className="pointer-events-none absolute left-0 top-0 h-full w-6 bg-gradient-to-r from-base-900 to-transparent" />
      <div className="pointer-events-none absolute right-0 top-0 h-full w-6 bg-gradient-to-l from-base-900 to-transparent" />
    </div>
  );
}
