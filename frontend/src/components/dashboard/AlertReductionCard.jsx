import { useEffect, useRef, useState } from 'react';
import { Activity, Gauge } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Live alert-reduction KPI card.
 *
 * Consumes flat metric fields produced by GET /api/metrics:
 *   - total_raw_events
 *   - total_incidents
 *   - alert_reduction_ratio  (0..100)
 *   - avg_mttd_seconds
 *   - events_per_minute
 */
function useCountUp(target, duration = 1500) {
  const [value, setValue] = useState(0);
  const rafRef = useRef(null);
  const startRef = useRef(null);
  const fromRef = useRef(0);

  useEffect(() => {
    const to = Number.isFinite(target) ? Number(target) : 0;
    fromRef.current = value;
    startRef.current = null;

    const tick = (ts) => {
      if (startRef.current == null) startRef.current = ts;
      const elapsed = ts - startRef.current;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(fromRef.current + (to - fromRef.current) * eased);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);

  return value;
}

function fmtInt(n) {
  if (!Number.isFinite(n)) return '0';
  return Math.round(n).toLocaleString();
}

export default function AlertReductionCard({ metrics = {}, className = '' }) {
  const totalRaw     = Number(metrics.total_raw_events ?? metrics.raw_events?.total ?? 0);
  const totalInc     = Number(metrics.total_incidents ?? metrics.correlated_incidents ?? 0);
  const ratio        = Number(metrics.alert_reduction_ratio ?? metrics.alert_reduction_percentage ?? 0);
  const avgMttd      = metrics.avg_mttd_seconds;
  const eventsPerMin = Number(metrics.events_per_minute ?? 0);

  const animRatio = useCountUp(ratio, 1500);
  const barPct = Math.max(0, Math.min(100, animRatio));

  return (
    <div className={cn(
      'rounded-lg border border-base-800 bg-base-900 p-4 flex flex-col gap-3',
      className,
    )}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-base-800 bg-base-950">
            <Gauge className="h-4 w-4 text-accent" />
          </div>
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider text-base-500">Alert Reduction</div>
            <div className="text-[11px] text-base-400">Raw events → correlated incidents</div>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          live
        </span>
      </div>

      {/* Flow */}
      <div className="flex flex-col gap-1 font-mono">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-base-100 tabular-nums">{fmtInt(totalRaw)}</span>
          <span className="text-[11px] text-base-500">raw events</span>
        </div>
        <div className="text-base-500 text-xs pl-1">↓</div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-accent tabular-nums">{fmtInt(totalInc)}</span>
          <span className="text-[11px] text-base-500">correlated incidents</span>
        </div>
      </div>

      {/* Ratio bar */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-base-500">Reduction ratio</span>
          <span className="text-lg font-semibold text-emerald-300 tabular-nums font-mono">
            {animRatio.toFixed(2)}%
          </span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-base-950 border border-base-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-emerald-400 to-accent transition-[width] duration-300"
            style={{ width: `${barPct}%` }}
          />
        </div>
      </div>

      {/* Footer stats */}
      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-base-800">
        <div className="flex items-center gap-1.5">
          <Activity className="h-3 w-3 text-base-500" />
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-wider text-base-500">Avg MTTD</span>
            <span className="text-xs font-mono font-semibold text-base-200 tabular-nums">
              {avgMttd != null ? `${Number(avgMttd).toFixed(2)}s` : '—'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <Activity className="h-3 w-3 text-base-500" />
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-wider text-base-500">Events/min</span>
            <span className="text-xs font-mono font-semibold text-base-200 tabular-nums">
              {eventsPerMin.toFixed(1)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
