import { useMemo, useCallback } from 'react';
import { cn } from '@/lib/utils';

function buildBins(events, bucketCount) {
  if (!events?.length) {
    return { bins: [], min: 0, max: 0, span: 1, peak: 0 };
  }
  const times = events.map((e) => new Date(e.timestamp).getTime()).filter((t) => !Number.isNaN(t));
  if (!times.length) {
    return { bins: [], min: 0, max: 0, span: 1, peak: 0 };
  }
  const min = Math.min(...times);
  const max = Math.max(...times);
  const span = Math.max(1, max - min);
  const bins = new Array(bucketCount).fill(0);
  times.forEach((t) => {
    const idx = Math.min(bucketCount - 1, Math.floor(((t - min) / span) * bucketCount));
    bins[idx] += 1;
  });
  const peak = bins.indexOf(Math.max(...bins));
  return { bins, min, max, span, peak };
}

/**
 * Histogram ribbon — click a bucket to narrow the visible time window (correlation view).
 *
 * @param {{
 *   events: Record<string, unknown>[];
 *   bucketCount?: number;
 *   activeBin: number | null;
 *   onSelectBin: (payload: { start: number; end: number; binIndex: number }) => void;
 * }} props
 */
export default function TimelineRibbon({ events, bucketCount = 40, activeBin, onSelectBin }) {
  const { bins, min, max, span, peak } = useMemo(
    () => buildBins(events, bucketCount),
    [events, bucketCount]
  );
  const maxVal = Math.max(...bins, 1);

  const barWidth = 100 / bucketCount;

  const handleBarClick = useCallback(
    (i) => {
      const start = min + (i / bucketCount) * span;
      const end = min + ((i + 1) / bucketCount) * span;
      onSelectBin({ start, end, binIndex: i });
    },
    [min, span, bucketCount, onSelectBin]
  );

  return (
    <section className="rounded-lg border border-base-800 bg-base-900 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-base-200">Timeline ribbon</h3>
          <p className="font-mono text-[10px] text-base-500">Click a bar to filter the table to that window · peak ≈ attack density</p>
        </div>
        <span className="font-mono text-[10px] text-base-600">
          {bins.length ? `${new Date(min).toLocaleTimeString()} → ${new Date(max).toLocaleTimeString()}` : '—'}
        </span>
      </div>

      {bins.length === 0 ? (
        <div className="py-8 text-center text-xs text-base-600">No events to plot</div>
      ) : (
        <svg
          className="h-24 w-full text-base-600"
          viewBox="0 0 100 32"
          preserveAspectRatio="none"
          role="img"
          aria-label="Event volume by time bucket"
        >
          {bins.map((c, i) => {
            const h = Math.max(1, (c / maxVal) * 28);
            const x = i * barWidth;
            const isPeak = i === peak;
            const isActive = activeBin === i;
            return (
              <g key={i} className="cursor-pointer" onClick={() => handleBarClick(i)} role="presentation">
                <rect
                  x={x + 0.1}
                  y={32 - h}
                  width={barWidth - 0.2}
                  height={h}
                  rx={0.4}
                  className={cn(
                    'pointer-events-auto transition-colors hover:opacity-90',
                    isActive && 'fill-accent',
                    !isActive && isPeak && 'fill-base-300/90',
                    !isActive && !isPeak && 'fill-base-700'
                  )}
                />
              </g>
            );
          })}
        </svg>
      )}
    </section>
  );
}
