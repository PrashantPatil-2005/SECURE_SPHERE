import { cn } from '@/lib/utils';

/**
 * @param {{
 *   label: string;
 *   value: React.ReactNode;
 *   sub?: React.ReactNode;
 *   icon?: React.ComponentType<{ className?: string }>;
 *   emphasize?: boolean;
 *   className?: string;
 * }} props
 */
export default function KPICard({ label, value, sub, icon: Icon, emphasize, className }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-base-800 bg-base-900 p-4 transition-colors',
        emphasize && 'border-red-500/30 ring-1 ring-red-500/15',
        className
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        {Icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-base-800 bg-base-950">
            <Icon className="h-4 w-4 text-base-400" />
          </div>
        )}
        <span className="text-[10px] font-semibold uppercase tracking-wider text-base-500">{label}</span>
      </div>
      <div className="text-2xl font-semibold tracking-tight text-base-100">{value}</div>
      {sub && <div className="mt-1 text-xs text-base-500">{sub}</div>}
    </div>
  );
}
