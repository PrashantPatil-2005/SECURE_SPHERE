import { cn } from '@/lib/utils';
import { cva } from 'class-variance-authority';

const badgeVariants = cva(
  'inline-flex items-center px-2 py-0.5 rounded text-2xs font-semibold uppercase tracking-wider border transition-colors duration-200',
  {
    variants: {
      variant: {
        critical: 'bg-red-500/10 text-red-400 border-red-500/20',
        high: 'bg-base-800/50 text-base-200 border-base-700',
        medium: 'bg-base-800/40 text-base-300 border-base-700',
        low: 'bg-base-800/30 text-base-400 border-base-800',
        info: 'bg-base-900/60 text-base-500 border-base-800',
        accent: 'bg-accent-muted text-accent border-accent/20',
        default: 'bg-base-800/40 text-base-400 border-base-800/80',
        active: 'bg-red-500/10 text-red-400 border-red-500/20',
        acknowledged: 'bg-accent-muted text-accent border-accent/20',
        escalated: 'bg-red-500/15 text-red-300 border-red-500/30',
        suppressed: 'bg-base-800/50 text-base-400 border-base-700',
        open: 'bg-red-500/10 text-red-400 border-red-500/20',
        investigating: 'bg-base-800/45 text-base-300 border-base-700',
        resolved: 'bg-base-800/35 text-base-400 border-base-800',
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
