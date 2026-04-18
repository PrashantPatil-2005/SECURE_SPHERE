import { Badge } from '@/components/ui/Badge';
import SeverityDot from './SeverityDot';
import { formatTimestamp, safeString } from '@/lib/utils';

/**
 * @param {{
 *   event: Record<string, unknown>;
 *   flash?: boolean;
 * }} props
 */
export default function FeedItem({ event, flash }) {
  const sev = event?.severity;
  const layerRaw = safeString(event?.source_layer || 'N/A');
  const layer = layerRaw.toUpperCase();
  const ip = event?.source_entity?.ip || event?.source_entity?.service;

  return (
    <div
      className={
        flash
          ? 'flex items-center gap-3 rounded-lg border border-base-800/80 bg-base-950/50 px-3 py-2 animate-flash-row'
          : 'flex items-center gap-3 rounded-lg border border-transparent px-3 py-2 transition-colors hover:border-base-800 hover:bg-base-950/40'
      }
    >
      <SeverityDot level={sev} />
      <time className="w-14 shrink-0 font-mono text-[11px] text-base-500">{formatTimestamp(event?.timestamp)}</time>
      <p className="min-w-0 flex-1 truncate text-xs font-medium text-base-200">{safeString(event?.event_type)}</p>
      <span className="shrink-0 font-mono text-[11px] text-base-400">{ip ? safeString(ip) : '—'}</span>
      <Badge variant="default" className="shrink-0 border-base-700 text-[9px] text-base-400">
        {layer}
      </Badge>
    </div>
  );
}
