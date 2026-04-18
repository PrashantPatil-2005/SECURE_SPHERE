import { AlertTriangle } from 'lucide-react';
import IncidentItem from './IncidentItem';

/**
 * @param {{
 *   incidents: Record<string, unknown>[];
 *   title?: string;
 *   maxItems?: number;
 *   selectedId?: string | null;
 *   onSelect?: (id: string) => void;
 * }} props
 */
export default function IncidentList({
  incidents = [],
  title = 'Active incidents',
  maxItems = 12,
  selectedId,
  onSelect,
}) {
  const slice = incidents.slice(0, maxItems);

  return (
    <section className="flex min-h-0 flex-col rounded-lg border border-base-800 bg-base-900">
      <div className="flex items-center justify-between border-b border-base-800 px-4 py-3">
        <h3 className="text-sm font-semibold text-base-200">{title}</h3>
        {incidents.length > 0 && (
          <span className="rounded-full border border-base-700 bg-base-950/50 px-2 py-0.5 font-mono text-[10px] font-semibold text-base-300">
            {incidents.length}
          </span>
        )}
      </div>
      <div className="max-h-[min(60vh,520px)] min-h-[220px] overflow-y-auto px-4 pb-3 pt-1">
        {slice.length > 0 ? (
          slice.map((inc) => (
            <IncidentItem
              key={safeId(inc)}
              incident={inc}
              selected={selectedId != null && safeId(inc) === selectedId}
              onSelect={() => onSelect?.(safeId(inc))}
            />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 py-14 text-xs text-base-500">
            <AlertTriangle className="h-6 w-6 opacity-30" />
            No incidents detected
          </div>
        )}
      </div>
    </section>
  );
}

function safeId(inc) {
  return String(inc?.incident_id ?? '');
}
