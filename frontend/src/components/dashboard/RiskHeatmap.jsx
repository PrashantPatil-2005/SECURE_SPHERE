import RiskRow from './RiskRow';
import { safeString } from '@/lib/utils';

/**
 * @param {{
 *   riskScores?: Record<string, { current_score?: number; threat_level?: string }>;
 *   maxRows?: number;
 *   title?: string;
 * }} props
 */
export default function RiskHeatmap({ riskScores = {}, maxRows = 8, title = 'Risk heatmap' }) {
  const entries = Object.entries(riskScores || {}).filter(([, v]) => v);
  const slice = entries.slice(0, maxRows);
  const maxScore = slice.reduce((m, [, d]) => Math.max(m, d?.current_score || 0), 0) || 1;

  return (
    <section className="flex min-h-0 flex-col rounded-lg border border-base-800 bg-base-900">
      <div className="flex items-center justify-between border-b border-base-800 px-4 py-3">
        <h3 className="text-sm font-semibold text-base-200">{title}</h3>
        <span className="font-mono text-[10px] text-base-500">{entries.length} entities</span>
      </div>
      <div className="max-h-[min(40vh,320px)] space-y-3 overflow-y-auto p-4">
        {slice.length > 0 ? (
          slice.map(([ip, data]) => {
            const score = data?.current_score || 0;
            const level = safeString(data?.threat_level || 'normal').toLowerCase();
            const pct = maxScore > 0 ? Math.min(100, (score / (maxScore * 1.25)) * 100) : 0;
            return (
              <RiskRow key={ip} label={ip} score={score} level={level} percent={pct} />
            );
          })
        ) : (
          <p className="py-8 text-center text-sm text-base-500">No risk data available</p>
        )}
      </div>
    </section>
  );
}
