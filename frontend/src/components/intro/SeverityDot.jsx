import { cn } from '@/lib/utils';

const LEVEL = {
  critical: 'bg-red-500 shadow-[0_0_0_2px_rgba(239,68,68,0.35)]',
  high: 'bg-base-300',
  medium: 'bg-base-400',
  low: 'bg-base-500',
  normal: 'bg-base-600',
};

export default function SeverityDot({ level = 'normal', className }) {
  return (
    <span
      className={cn(
        'inline-block h-2 w-2 shrink-0 rounded-full transition-colors duration-200',
        LEVEL[level] ?? LEVEL.normal,
        className
      )}
      aria-hidden
    />
  );
}
