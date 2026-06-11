import { cn } from '@/lib/utils';

export function Input({ className, mono, ...props }) {
  return (
    <input
      className={cn(
        'h-9 w-full rounded-lg border border-base-800 bg-base-950/50 px-3 text-sm text-base-100',
        'transition-colors duration-200 placeholder:text-base-500 outline-none',
        'focus:border-accent/50 focus:ring-2 focus:ring-accent/15',
        mono ? 'font-mono tabular-nums' : 'font-sans',
        className
      )}
      {...props}
    />
  );
}

export function Select({ children, className, ...props }) {
  return (
    <select
      className={cn(
        'h-9 cursor-pointer rounded-lg border border-base-800 bg-base-900 px-2.5 text-sm text-base-200',
        'outline-none transition-colors duration-200 focus:border-accent/50 focus:ring-2 focus:ring-accent/15',
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}
