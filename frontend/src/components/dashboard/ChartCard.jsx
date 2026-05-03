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
    <section className={cn('rounded-[10px] border border-base-800 bg-base-900', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-base-800 px-3.5 py-2.5">
        <div>
          <h3 className="text-[12px] font-semibold tracking-wide text-base-200">{title}</h3>
          {description && <p className="mt-0.5 text-[10px] text-base-500">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className={cn('p-4', bodyClassName)}>{children}</div>
    </section>
  );
}
