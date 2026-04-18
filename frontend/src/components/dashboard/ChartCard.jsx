import { cn } from '@/lib/utils';

/**
 * @param {{
 *   title: string;
 *   description?: string;
 *   actions?: React.ReactNode;
 *   children: React.ReactNode;
 *   className?: string;
 *   bodyClassName?: string;
 * }} props
 */
export default function ChartCard({ title, description, actions, children, className, bodyClassName }) {
  return (
    <section className={cn('rounded-lg border border-base-800 bg-base-900', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-base-800 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-base-200">{title}</h3>
          {description && <p className="mt-0.5 text-xs text-base-500">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className={cn('p-4', bodyClassName)}>{children}</div>
    </section>
  );
}
