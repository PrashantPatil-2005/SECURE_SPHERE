import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

export function Spinner({ className, size = 20 }) {
  return <Loader2 className={cn('animate-spin text-accent', className)} size={size} />;
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64 gap-3">
      <Spinner size={24} />
      <span className="text-sm text-base-400">Loading...</span>
    </div>
  );
}

export function Skeleton({ className }) {
  return (
    <div className={cn(
      'rounded-lg bg-gradient-to-r from-base-800 via-base-700 to-base-800 bg-[length:200%_100%] animate-pulse',
      className
    )} />
  );
}
