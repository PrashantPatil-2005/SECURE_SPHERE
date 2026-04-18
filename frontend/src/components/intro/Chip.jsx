import { cn } from '@/lib/utils';

const VARIANT = {
  critical: 'border-red-500/30 bg-red-500/10 text-red-300',
  high: 'border-base-700 bg-base-800/60 text-base-200',
  medium: 'border-base-700 bg-base-800/45 text-base-300',
  low: 'border-base-800 bg-base-800/35 text-base-400',
  info: 'border-base-800 bg-base-900/50 text-base-500',
  neutral: 'border-base-800 bg-base-800/40 text-base-300',
};

export default function Chip({ variant = 'neutral', children, className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border px-2 py-1 font-mono text-xs font-medium transition-colors duration-200',
        VARIANT[variant] ?? VARIANT.neutral,
        className
      )}
    >
      {children}
    </span>
  );
}
