import { Badge } from '@/components/ui/Badge';
import SeverityDot from './SeverityDot';
import { formatIncidentPath, killChainStepCount } from './incidentFormat';
import { cn, getSeverityString, relativeTime, safeString } from '@/lib/utils';

/**
 * @param {{
 *   incident: Record<string, unknown>;
 *   selected?: boolean;
 *   onSelect?: () => void;
 * }} props
 */
export default function IncidentItem({ incident, selected, onSelect }) {
  const title = safeString(incident?.title) || 'Untitled incident';
  const path = formatIncidentPath(incident);
  const steps = killChainStepCount(incident);
  const sev = getSeverityString(incident?.severity);
  const techniques = Array.isArray(incident?.mitre_techniques) ? incident.mitre_techniques : [];

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'flex w-full items-start gap-3 border-t border-base-800 py-3 text-left transition-colors first:border-t-0 first:pt-0',
        selected ? 'bg-base-950/80 ring-1 ring-inset ring-accent/25' : 'hover:bg-base-950/50'
      )}
    >
      <div className="pt-1">
        <SeverityDot level={incident?.severity} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-base-200">{title}</p>
        <p className="mt-0.5 text-xs text-base-400">
          {path || 'Path unknown'}
          {steps > 0 && (
            <>
              {' '}
              · {steps} step{steps === 1 ? '' : 's'}
            </>
          )}
        </p>
        {techniques.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {techniques.slice(0, 6).map((t) => (
              <span
                key={safeString(t)}
                className="rounded border border-base-700 bg-base-950 px-1.5 py-0.5 font-mono text-[9px] text-base-300"
              >
                {safeString(t)}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <Badge variant={sev}>{sev}</Badge>
        <time className="font-mono text-[10px] text-base-500">{relativeTime(incident?.timestamp)}</time>
      </div>
    </button>
  );
}
