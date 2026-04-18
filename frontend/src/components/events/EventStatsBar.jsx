import { getSeverityString } from '@/lib/utils';

/**
 * @param {{
 *   events: Record<string, unknown>[];
 *   filteredEvents: Record<string, unknown>[];
 * }} props
 */
export default function EventStatsBar({ events, filteredEvents }) {
  const crit = filteredEvents.filter((e) => getSeverityString(e.severity) === 'critical').length;
  const high = filteredEvents.filter((e) => getSeverityString(e.severity) === 'high').length;

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-base-800 pb-3 font-mono text-xs text-base-400">
      <span>
        Window: <strong className="text-base-200">{events.length}</strong>
      </span>
      <span>
        Shown: <strong className="text-base-200">{filteredEvents.length}</strong>
      </span>
      <span>
        Crit: <strong className="text-red-500">{crit}</strong>
      </span>
      <span>
        High: <strong className="text-base-200">{high}</strong>
      </span>
    </div>
  );
}
