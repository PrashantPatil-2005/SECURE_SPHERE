import { cn } from '@/lib/utils';

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        'h-8 w-full rounded-lg border border-white/[0.07] bg-white/[0.03] px-3 text-sm text-base-100',
        'placeholder:text-base-500 outline-none transition-all duration-150',
        'focus:border-accent focus:ring-2 focus:ring-accent/10',
        'font-mono',
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
        'h-8 rounded-lg border border-white/[0.07] bg-base-800 px-2.5 text-xs text-base-300',
        'outline-none transition-all focus:border-accent cursor-pointer',
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}
