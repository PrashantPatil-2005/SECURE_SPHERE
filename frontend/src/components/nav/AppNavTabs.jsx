import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { NAV_ITEMS } from './navConfig';

/**
 * Compact horizontal links for Tweaks “Quick jump”.
 *
 * @param {{ badges?: Record<string, number>; className?: string }} props
 */
export default function AppNavTabs({ badges = {}, className }) {
  return (
    <div className={cn('flex flex-wrap gap-1.5 border-b border-base-800 pb-3', className)}>
      {NAV_ITEMS.map((item) => {
        const badge = badges[item.id];
        return (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) =>
              cn(
                'rounded-md border px-2 py-1 font-mono text-[10px] transition-colors',
                isActive
                  ? 'border-accent/35 bg-accent/10 text-accent'
                  : 'border-base-800 text-base-500 hover:border-base-700 hover:text-base-300'
              )
            }
            end={item.path === '/intro'}
          >
            {item.label}
            {typeof badge === 'number' && badge > 0 && (
              <span className="ml-1 text-base-600">({badge > 99 ? '99+' : badge})</span>
            )}
          </NavLink>
        );
      })}
    </div>
  );
}
