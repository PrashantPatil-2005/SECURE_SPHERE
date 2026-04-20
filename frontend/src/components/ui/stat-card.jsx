import { cn } from '@/lib/utils';

export function StatCard({ label, value, icon: Icon, color = 'accent', sub, pulse, glow, className }) {
  const colorMap = {
    accent: { text: 'text-accent', bg: 'bg-accent/10', border: 'border-accent/40' },
    red: { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/40' },
    orange: { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/40' },
    amber: { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/40' },
    cyan: { text: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/40' },
    green: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/40' },
    violet: { text: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/40' },
    muted: { text: 'text-base-400', bg: 'bg-base-950/40', border: 'border-base-800' },
  };

  const c = colorMap[color] || colorMap.accent;

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-[10px] border bg-base-900 p-5',
        'transition-all duration-300 ease-out hover:-translate-y-0.5 hover:border-base-700',
        glow ? c.border : 'border-base-800',
        className
      )}
    >
      {/* soft accent glow in corner */}
      <div
        className={cn(
          'pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full blur-2xl opacity-40 transition-opacity duration-500 group-hover:opacity-70',
          c.bg
        )}
      />

      <div className="relative mb-3 flex items-center gap-2">
        {Icon && (
          <div
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3',
              c.bg
            )}
          >
            <Icon className={cn('h-4 w-4', c.text)} />
          </div>
        )}
        <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-base-400">{label}</span>
      </div>

      <div
        className={cn(
          'relative mb-1.5 text-3xl font-semibold leading-none tracking-tight',
          c.text === 'text-base-400' ? 'text-base-100' : c.text
        )}
      >
        {value}
        {pulse && (
          <span className={cn('ml-2 inline-block h-1.5 w-1.5 animate-pulse-glow align-middle rounded-full', c.bg.replace('/10', '/80'))} />
        )}
      </div>

      {sub && <div className="relative text-xs text-base-500">{sub}</div>}
    </div>
  );
}
