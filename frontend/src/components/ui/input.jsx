import { cn } from '@/lib/utils';

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        'h-8 w-full rounded-lg border border-base-800 bg-base-950/50 px-3 font-mono text-sm text-base-100',
        'transition-colors duration-200 placeholder:text-base-500 outline-none',
        'focus:border-accent focus:ring-2 focus:ring-accent/10',
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
        'h-8 cursor-pointer rounded-lg border border-base-800 bg-base-800 px-2.5 text-xs text-base-300',
        'outline-none transition-colors duration-200 focus:border-accent',
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}
