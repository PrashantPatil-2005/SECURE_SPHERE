import { cn } from '@/lib/utils';

export function Card({ children, className, glow, ...props }) {
  return (
    <div
      className={cn(
        'rounded-[10px] border border-white/[0.07] bg-base-800',
        'transition-colors duration-200',
        glow && 'border-severity-critical/40',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }) {
  return (
    <div className={cn('flex items-center justify-between px-4 py-3 border-b border-white/[0.05]', className)}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className }) {
  return (
    <h3 className={cn('text-sm font-semibold text-base-100 dark:text-base-100', className)}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className }) {
  return (
    <div className={cn('p-4', className)}>
      {children}
    </div>
  );
}
