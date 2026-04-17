import { cn } from '@/lib/utils';
import { cva } from 'class-variance-authority';

const badgeVariants = cva(
  'inline-flex items-center px-2 py-0.5 rounded text-2xs font-semibold uppercase tracking-wider border',
  {
    variants: {
      variant: {
        critical: 'bg-red-500/10 text-red-400 border-red-500/20',
        high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
        medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        low: 'bg-green-500/10 text-green-400 border-green-500/20',
        info: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
        accent: 'bg-accent-muted text-accent border-accent/20',
        default: 'bg-base-700/50 text-base-400 border-white/5',
        // Backend triage vocabulary
        active: 'bg-red-500/10 text-red-400 border-red-500/20',
        acknowledged: 'bg-accent-muted text-accent border-accent/20',
        escalated: 'bg-red-500/15 text-red-300 border-red-500/30',
        suppressed: 'bg-base-700/60 text-base-400 border-white/10',
        // Legacy status vocab (mock-data.js)
        open: 'bg-red-500/10 text-red-400 border-red-500/20',
        investigating: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        resolved: 'bg-green-500/10 text-green-400 border-green-500/20',
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
