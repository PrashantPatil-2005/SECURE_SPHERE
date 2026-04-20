import { cn } from '@/lib/utils';
import { cva } from 'class-variance-authority';

const buttonVariants = cva(
  'relative inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-1 focus-visible:ring-offset-base-950 disabled:pointer-events-none disabled:opacity-40 cursor-pointer active:scale-[0.98] hover:-translate-y-px',
  {
    variants: {
      variant: {
        primary:
          'bg-gradient-to-br from-accent to-accent-hover text-base-950 hover:shadow-lg hover:shadow-accent/30 shadow-sm shadow-accent/20',
        secondary:
          'border border-base-800 bg-base-950/50 text-base-200 hover:border-accent/40 hover:bg-base-900/80 hover:text-base-100',
        ghost: 'text-base-400 hover:bg-accent/10 hover:text-accent',
        danger:
          'border border-red-500/40 bg-red-500/10 text-red-300 hover:border-red-500/60 hover:bg-red-500/20 hover:shadow-lg hover:shadow-red-500/20',
        success:
          'border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:border-emerald-500/60 hover:bg-emerald-500/20',
        icon: 'rounded-lg text-base-400 hover:bg-accent/10 hover:text-accent',
      },
      size: {
        sm: 'h-7 px-2.5 text-xs',
        md: 'h-8 px-3 text-sm',
        lg: 'h-10 px-5 text-sm',
        icon: 'h-8 w-8',
      },
    },
    defaultVariants: {
      variant: 'secondary',
      size: 'md',
    },
  }
);

export function Button({ children, variant, size, className, ...props }) {
  return (
    <button className={cn(buttonVariants({ variant, size }), className)} {...props}>
      {children}
    </button>
  );
}
