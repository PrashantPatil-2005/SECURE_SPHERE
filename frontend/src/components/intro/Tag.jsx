import { cn } from '@/lib/utils';

export default function Tag({ label, className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border border-base-800 bg-base-800 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-base-400',
        className
      )}
    >
      {label}
    </span>
  );
}
