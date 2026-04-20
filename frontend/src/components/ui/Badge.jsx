import { cn } from '@/lib/utils';
import { cva } from 'class-variance-authority';

const badgeVariants = cva(
  'inline-flex items-center px-2 py-0.5 rounded text-2xs font-semibold uppercase tracking-wider border transition-all duration-200 hover:brightness-110',
  {
    variants: {
      variant: {
        critical: 'bg-red-500/15 text-red-300 border-red-500/40 shadow-[0_0_10px_-2px_rgba(239,68,68,0.45)]',
        high: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
        medium: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
        low: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40',
        info: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
        accent: 'bg-accent-muted text-accent border-accent/30',
        default: 'bg-base-800/50 text-base-300 border-base-700',
        active: 'bg-red-500/15 text-red-300 border-red-500/40 shadow-[0_0_10px_-2px_rgba(239,68,68,0.45)]',
        acknowledged: 'bg-violet-500/15 text-violet-300 border-violet-500/40',
        escalated: 'bg-pink-500/15 text-pink-300 border-pink-500/40 shadow-[0_0_10px_-2px_rgba(236,72,153,0.45)]',
        suppressed: 'bg-base-800/60 text-base-400 border-base-700',
        open: 'bg-red-500/15 text-red-300 border-red-500/40',
        investigating: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
        resolved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export function Badge({ children, variant, className }) {
  const resolvedVariant = variant || 'default';
  return (
    <span className={cn(badgeVariants({ variant: resolvedVariant }), className)}>
      {children || resolvedVariant}
    </span>
  );
}
