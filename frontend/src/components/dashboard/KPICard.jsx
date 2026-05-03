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
        'rounded-[10px] border bg-base-900 px-3.5 py-3 transition-colors',
        emphasize
          ? 'border-sev-critical-border shadow-[inset_0_0_0_1px_rgba(239,68,68,0.08)]'
          : 'border-base-800',
        className
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-base-600">{label}</span>
        {Icon && <Icon className={cn('h-3.5 w-3.5', emphasize ? 'text-sev-critical' : 'text-base-600')} />}
      </div>
      <div
        className={cn(
          'font-mono text-[24px] font-bold leading-none tracking-tight',
          emphasize ? 'text-sev-critical' : 'text-base-100'
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-1.5 text-[10px] text-base-500">{sub}</div>}
    </div>
  );
}
