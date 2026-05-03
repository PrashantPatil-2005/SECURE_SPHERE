import { cn } from '@/lib/utils';
import KPICard from './KPICard';

/**
 * @param {{
 *   items: Array<{
 *     id: string;
 *     label: string;
 *     value: React.ReactNode;
 *     sub?: React.ReactNode;
 *     icon?: React.ComponentType<{ className?: string }>;
 *     emphasize?: boolean;
 *   }>;
 *   className?: string;
 *   columnsClassName?: string;
 * }} props
 */
export default function KPIBar({ items, className, columnsClassName }) {
  return (
    <div className={cn('grid gap-2.5', columnsClassName ?? 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5', className)}>
      {items.map((item) => (
        <KPICard
          key={item.id}
          label={item.label}
          value={item.value}
          sub={item.sub}
          icon={item.icon}
          emphasize={item.emphasize}
        />
      ))}
    </div>
  );
}
