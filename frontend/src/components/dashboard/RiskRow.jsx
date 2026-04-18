import { cn, safeString } from '@/lib/utils';

/**
 * Threat levels — red reserved for `critical` only.
 */
const LEVEL_RAIL = {
  critical: 'bg-red-500',
  threatening: 'bg-base-300',
  suspicious: 'bg-base-400',
  normal: 'bg-base-500',
};

const LEVEL_FILL = {
  critical: 'fill-red-500',
  threatening: 'fill-base-300',
  suspicious: 'fill-base-400',
  normal: 'fill-base-500',
};

/**
 * @param {{
 *   label: string;
 *   score: number;
 *   level: string;
 *   percent: number;
 * }} props
 */
export default function RiskRow({ label, score, level, percent }) {
  const lv = safeString(level).toLowerCase();
  const rail = LEVEL_RAIL[lv] ?? 'bg-base-500';
  const fill = LEVEL_FILL[lv] ?? 'fill-base-500';
  const pct = Math.max(0, Math.min(100, percent));

  return (
    <div className="relative overflow-hidden rounded-lg border border-base-800 bg-base-950 p-3 transition-colors duration-200">
      <div className={cn('absolute bottom-0 left-0 top-0 w-1', rail)} aria-hidden />
      <div className="mb-2 flex items-center justify-between pl-2">
        <span className="font-mono text-sm font-semibold text-base-200">{label}</span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-base-200">{Math.round(score)}</span>
          <span className="rounded-full border border-base-700 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-base-400">
            {lv}
          </span>
        </div>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-base-800 pl-2">
        <svg className="h-full w-full" viewBox="0 0 100 2" preserveAspectRatio="none" aria-hidden>
          <rect x="0" y="0" width={pct} height="2" className={cn(fill)} />
        </svg>
      </div>
    </div>
  );
}
