import { ChevronRight, Server, Shield } from 'lucide-react';
import { cn, severityColor, layerColor, safeString, formatTimestamp } from '@/lib/utils';

/**
 * Renders a kill-chain as a horizontal step flow.
 *
 * Preferred input: `steps` = array of rich objects from Postgres kill_chains.steps
 *   { service_name, service?, layer?, event_type?, severity?, mitre?, technique?, timestamp? }
 *
 * Fallbacks (in order):
 *   - `servicePath` (array of strings)
 *   - `steps` as a number (count only — render placeholders)
 */
export default function KillChainTimeline({
  steps = [],
  servicePath = [],
  mitreTechniques = [],
  compact = false,
}) {
  const isRichSteps = Array.isArray(steps) && steps.length > 0 && typeof steps[0] === 'object';

  let nodes = [];
  if (isRichSteps) {
    nodes = steps.map((s, i) => ({
      service: s.service_name || s.service || s.source_service_name || `Step ${i + 1}`,
      layer: s.layer || s.source_layer || null,
      event: s.event_type || s.description || null,
      severity: s.severity || null,
      mitre: s.mitre || s.technique || (Array.isArray(s.mitre_techniques) ? s.mitre_techniques[0] : null),
      timestamp: s.timestamp || s.ts || null,
    }));
  } else if (servicePath.length > 0) {
    nodes = servicePath.map((svc, i) => ({
      service: safeString(svc),
      layer: null,
      event: null,
      severity: null,
      mitre: mitreTechniques[i] || null,
      timestamp: null,
    }));
  } else if (Number(steps) > 0) {
    nodes = Array.from({ length: Number(steps) }, (_, i) => ({
      service: `Step ${i + 1}`,
      layer: null, event: null, severity: null,
      mitre: mitreTechniques[i] || null, timestamp: null,
    }));
  } else {
    return null;
  }

  return (
    <div className="flex items-stretch gap-1 overflow-x-auto py-2 px-1">
      {nodes.map((node, i) => {
        const isFirst = i === 0;
        const isLast = i === nodes.length - 1;
        const sevHex = node.severity ? severityColor(node.severity) : null;
        const layerHex = node.layer ? layerColor(node.layer) : null;

        return (
          <div key={i} className="flex items-stretch gap-1 shrink-0">
            <div className={cn(
              'relative flex flex-col gap-1 px-3 py-2 rounded-lg border min-w-[140px] bg-base-900/60',
              'border-white/[0.06]',
              isFirst && 'border-accent/30 bg-accent/[0.05]',
              isLast && !isFirst && 'border-severity-critical/30 bg-severity-critical/[0.05]',
            )}>
              {/* Header row: step index + severity dot */}
              <div className="flex items-center justify-between gap-2">
                <span className="text-[9px] font-mono font-semibold text-base-500 uppercase tracking-wider">
                  {isFirst ? 'Start' : isLast ? 'End' : `Step ${i + 1}`}
                </span>
                {sevHex && (
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: sevHex, boxShadow: `0 0 4px ${sevHex}` }}
                    title={`severity: ${safeString(node.severity)}`}
                  />
                )}
              </div>

              {/* Service name */}
              <div className="flex items-center gap-1.5 min-w-0">
                <Server className="w-3 h-3 shrink-0 text-base-500" />
                <span className="text-[11px] font-semibold text-base-100 truncate" title={node.service}>
                  {node.service}
                </span>
              </div>

              {/* Event type */}
              {node.event && !compact && (
                <span className="text-[10px] text-base-400 truncate" title={node.event}>
                  {node.event}
                </span>
              )}

              {/* MITRE + layer + time */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {node.mitre && (
                  <span className="inline-flex items-center gap-1 text-[9px] font-mono px-1 py-0.5 rounded bg-accent/[0.08] text-accent border border-accent/15">
                    <Shield className="w-2.5 h-2.5" />
                    {safeString(node.mitre)}
                  </span>
                )}
                {node.layer && (
                  <span
                    className="text-[9px] font-mono px-1 py-0.5 rounded border uppercase tracking-wider"
                    style={{
                      color: layerHex,
                      borderColor: `${layerHex}30`,
                      backgroundColor: `${layerHex}12`,
                    }}
                  >
                    {safeString(node.layer)}
                  </span>
                )}
                {node.timestamp && (
                  <span className="text-[9px] font-mono text-base-500 ml-auto">
                    {formatTimestamp(node.timestamp)}
                  </span>
                )}
              </div>
            </div>

            {!isLast && (
              <div className="flex items-center">
                <ChevronRight className="w-4 h-4 text-base-500 shrink-0" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
