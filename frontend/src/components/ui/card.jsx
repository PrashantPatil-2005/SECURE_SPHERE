import { cn } from '@/lib/utils';

export function Card({ children, className, glow, ...props }) {
  return (
    <div
      className={cn(
        'rounded-[10px] border border-base-800 bg-base-900',
        'transition-colors duration-200',
        glow && 'border-red-500/35',
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
    <div
      className={cn(
        'flex min-h-[44px] items-center justify-between border-b border-base-800 px-4 py-2.5',
        'bg-white/[0.015]',
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, className }) {
  return (
    <h3 className={cn('type-eyebrow text-base-400', className)}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className }) {
  return <div className={cn('p-4', className)}>{children}</div>;
}
