import { forwardRef } from 'react';
import SeverityDot from '@/components/dashboard/SeverityDot';
import { cn } from '@/lib/utils';

const HIGHLIGHT_IPS = new Set(['10.0.2.4']);

/**
 * @param {{
 *   row: {
 *     id: string;
 *     raw: Record<string, unknown>;
 *     timeLabel: string;
 *     severity: string;
 *     layer: string;
 *     event: string;
 *     service: string;
 *     src: string;
 *     target: string;
 *     mitre: string;
 *   };
 *   selected?: boolean;
 *   correlated?: boolean;
 *   flash?: boolean;
 *   onClick?: () => void;
 * }} props
 */
const EventRow = forwardRef(function EventRow({ row, selected, correlated, flash, onClick }, ref) {
  const ipHighlight = HIGHLIGHT_IPS.has(row.src);

  return (
    <tr
      ref={ref}
      onClick={onClick}
      className={cn(
        'cursor-pointer border-b border-base-800 text-sm transition-colors hover:bg-base-950/80',
        flash && 'animate-flash-row',
        selected && 'bg-base-950 ring-1 ring-inset ring-base-700',
        correlated && 'bg-base-900/60'
      )}
    >
      <td className="whitespace-nowrap py-1.5 pl-3 pr-2 font-mono text-xs text-base-500">{row.timeLabel}</td>
      <td className="py-1.5 pr-2">
        <SeverityDot level={row.raw?.severity} />
      </td>
      <td className="whitespace-nowrap py-1.5 pr-2 font-mono text-xs uppercase text-base-400">{row.layer}</td>
      <td className="max-w-[180px] truncate py-1.5 pr-2 font-mono text-xs text-base-200">{row.event}</td>
      <td className="max-w-[120px] truncate py-1.5 pr-2 font-mono text-xs text-base-400">{row.service}</td>
      <td
        className={cn(
          'whitespace-nowrap py-1.5 pr-2 font-mono text-xs',
          ipHighlight ? 'font-semibold text-base-100' : 'text-base-300'
        )}
      >
        {row.src}
      </td>
      <td className="max-w-[140px] truncate py-1.5 pr-2 font-mono text-xs text-base-500">{row.target}</td>
      <td className="whitespace-nowrap py-1.5 pr-3 font-mono text-xs text-base-400">
        {row.mitre ? <span className="rounded border border-base-700 bg-base-950 px-1 py-0.5">{row.mitre}</span> : '—'}
      </td>
    </tr>
  );
});

export default EventRow;
