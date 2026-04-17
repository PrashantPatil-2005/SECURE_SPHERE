import { cn } from '@/lib/utils';

export function StatCard({ label, value, icon: Icon, color = 'accent', sub, pulse, glow, className }) {
  const colorMap = {
    accent: { text: 'text-accent',     bg: 'bg-accent/10',     border: 'border-accent/40' },
    red:    { text: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/40' },
    orange: { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/40' },
    cyan:   { text: 'text-cyan-400',   bg: 'bg-cyan-500/10',   border: 'border-cyan-500/40' },
    green:  { text: 'text-green-400',  bg: 'bg-green-500/10',  border: 'border-green-500/40' },
    muted:  { text: 'text-base-400',   bg: 'bg-white/[0.03]',  border: 'border-white/[0.07]' },
  };

  const c = colorMap[color] || colorMap.accent;

  return (
    <div
      className={cn(
        'relative rounded-[10px] border bg-base-800 p-5',
        'transition-colors duration-200 hover:border-white/10',
        glow ? c.border : 'border-white/[0.07]',
        className
      )}
    >
      <div className="flex items-center gap-2 mb-3">
        {Icon && (
          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', c.bg)}>
            <Icon className={cn('w-4 h-4', c.text)} />
          </div>
        )}
        <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-base-400">
          {label}
        </span>
      </div>

      <div className={cn('text-3xl font-semibold tracking-tight leading-none mb-1.5', c.text === 'text-base-400' ? 'text-base-100' : c.text)}>
        {value}
        {pulse && (
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-severity-critical ml-2 animate-pulse-glow align-middle" />
        )}
      </div>

      {sub && (
        <div className="text-xs text-base-500">{sub}</div>
      )}
    </div>
  );
}
