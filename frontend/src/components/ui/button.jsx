import { cn } from '@/lib/utils';
import { cva } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:pointer-events-none disabled:opacity-40 cursor-pointer',
  {
    variants: {
      variant: {
        primary:
          'bg-accent text-base-950 hover:bg-accent-hover shadow-sm shadow-accent/20 hover:shadow-accent/30',
        secondary:
          'border border-base-800 bg-base-950/50 text-base-200 hover:border-base-700 hover:bg-base-900/80',
        ghost: 'text-base-400 hover:bg-base-950/40 hover:text-base-200',
        danger:
          'border border-base-700 bg-base-900 text-base-200 hover:border-base-600 hover:bg-base-950',
        icon: 'rounded-lg text-base-400 hover:bg-base-950/50 hover:text-base-200',
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
