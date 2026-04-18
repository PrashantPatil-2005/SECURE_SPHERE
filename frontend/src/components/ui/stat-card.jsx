import { cn } from '@/lib/utils';

export function StatCard({ label, value, icon: Icon, color = 'accent', sub, pulse, glow, className }) {
  const colorMap = {
    accent: { text: 'text-accent', bg: 'bg-accent/10', border: 'border-accent/40' },
    red: { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/40' },
    orange: { text: 'text-base-300', bg: 'bg-base-800/50', border: 'border-base-700' },
    cyan: { text: 'text-base-400', bg: 'bg-base-800/40', border: 'border-base-700' },
    green: { text: 'text-base-400', bg: 'bg-base-800/35', border: 'border-base-800' },
    muted: { text: 'text-base-400', bg: 'bg-base-950/40', border: 'border-base-800' },
  };

  const c = colorMap[color] || colorMap.accent;

  return (
    <div
      className={cn(
        'relative rounded-[10px] border bg-base-900 p-5',
        'transition-colors duration-200 hover:border-base-700',
        glow ? c.border : 'border-base-800',
        className
      )}
    >
      <div className="mb-3 flex items-center gap-2">
        {Icon && (
          <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg', c.bg)}>
            <Icon className={cn('h-4 w-4', c.text)} />
          </div>
        )}
        <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-base-400">{label}</span>
      </div>

      <div
        className={cn(
          'mb-1.5 text-3xl font-semibold leading-none tracking-tight',
          c.text === 'text-base-400' ? 'text-base-100' : c.text
        )}
      >
        {value}
        {pulse && (
          <span className="ml-2 inline-block h-1.5 w-1.5 animate-pulse-glow align-middle rounded-full bg-base-400" />
        )}
      </div>

      {sub && <div className="text-xs text-base-500">{sub}</div>}
    </div>
  );
}
