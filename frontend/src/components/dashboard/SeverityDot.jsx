import { cn } from '@/lib/utils';
import { severityDotClass } from './severityTokens';

/**
 * @param {{ level?: unknown; className?: string }} props
 */
export default function SeverityDot({ level, className }) {
  return (
    <span
      className={cn('inline-block h-2 w-2 shrink-0 rounded-full', severityDotClass(level), className)}
      aria-hidden
    />
  );
}
