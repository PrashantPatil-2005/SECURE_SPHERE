import { forwardRef } from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Filter-first query strip — combines freetext with canonical query hint.
 *
 * @param {{
 *   value: string;
 *   onChange: (v: string) => void;
 *   canonicalQuery: string;
 *   className?: string;
 * }} props
 */
const QueryBar = forwardRef(function QueryBar({ value, onChange, canonicalQuery, className }, ref) {
  const showHint = !value.trim();

  return (
    <div className={cn('rounded-lg border border-base-800 bg-base-900', className)}>
      <div className="border-b border-base-800 px-3 py-1.5">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-base-500">Query</span>
      </div>
      <div className="relative px-3 py-2">
        <Search className="pointer-events-none absolute left-5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-base-600" />
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search events, IPs, MITRE…"
          className="w-full rounded-md border border-base-800 bg-base-950 py-2 pl-9 pr-3 font-mono text-sm text-base-200 placeholder:text-base-600 outline-none ring-0 transition-colors focus:border-base-600"
          autoComplete="off"
          spellCheck={false}
        />
        {showHint && (
          <p className="mt-2 font-mono text-[11px] leading-relaxed text-base-600">
            Example: <span className="text-base-500">layer:auth AND severity&gt;=high</span>
          </p>
        )}
        {!showHint && canonicalQuery && (
          <p className="mt-2 truncate font-mono text-[11px] text-base-500" title={canonicalQuery}>
            Active: <span className="text-base-400">{canonicalQuery}</span>
          </p>
        )}
      </div>
    </div>
  );
});

export default QueryBar;
