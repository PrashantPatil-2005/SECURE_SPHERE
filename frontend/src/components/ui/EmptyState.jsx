import { Inbox } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No results',
  description,
  action,
  className,
  size = 'md',
}) {
  const padding = size === 'sm' ? 'py-8' : size === 'lg' ? 'py-20' : 'py-14';
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-base-800 bg-base-900/40 px-6 text-center',
        padding,
        className
      )}
    >
      <div aria-hidden="true" className="mb-1 flex h-10 w-10 items-center justify-center rounded-full border border-base-800 bg-base-950/60">
        <Icon className="h-5 w-5 text-base-500" />
      </div>
      <h3 className="text-sm font-semibold text-base-200">{title}</h3>
      {description && (
        <p className="max-w-md text-[12px] text-base-500">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
