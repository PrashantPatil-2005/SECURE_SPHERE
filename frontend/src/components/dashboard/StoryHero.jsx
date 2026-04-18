import { ShieldAlert, Ban, FolderOpen, UserPlus } from 'lucide-react';
import SeverityDot from './SeverityDot';
import { formatIncidentPath, killChainStepCount } from './incidentFormat';
import { safeString } from '@/lib/utils';

/**
 * Variant C — narrative-first SOC view (demo / exec walkthrough).
 *
 * @param {{
 *   incident: Record<string, unknown> | null;
 *   summary: string;
 *   onBlockIp?: () => void;
 *   onOpenIncident?: () => void;
 *   onAssign?: () => void;
 * }} props
 */
export default function StoryHero({ incident, summary, onBlockIp, onOpenIncident, onAssign }) {
  if (!incident) {
    return (
      <section className="rounded-xl border border-dashed border-base-700 bg-base-900/80 p-8 text-center">
        <ShieldAlert className="mx-auto mb-3 h-10 w-10 text-base-600" />
        <p className="text-sm text-base-400">No incident selected for story mode. Promote an alert or switch to Triage.</p>
      </section>
    );
  }

  const title = safeString(incident.title) || 'Incident';
  const path = formatIncidentPath(incident);
  const steps = killChainStepCount(incident);
  const techniques = Array.isArray(incident.mitre_techniques) ? incident.mitre_techniques : [];
  const sourceIp = incident.source_ip ? safeString(incident.source_ip) : null;

  return (
    <section className="relative overflow-hidden rounded-xl border border-base-800 bg-base-900">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-base-600/50 to-transparent" />
      <div className="flex flex-col gap-6 p-6 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1 space-y-4">
          <div className="flex items-start gap-3">
            <SeverityDot level={incident.severity} className="mt-1.5 h-2.5 w-2.5" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-base-500">Featured incident</p>
              <h2 className="mt-1 text-xl font-semibold tracking-tight text-base-100 md:text-2xl">{title}</h2>
            </div>
          </div>

          <p className="max-w-2xl text-sm leading-relaxed text-base-300">{summary}</p>

          <div className="flex flex-wrap gap-2">
            <span className="rounded-md border border-base-700 bg-base-950 px-2 py-1 font-mono text-[11px] text-base-300">
              {path || 'Path reconstructing…'}
            </span>
            {steps > 0 && (
              <span className="rounded-md border border-base-700 bg-base-950 px-2 py-1 font-mono text-[11px] text-base-400">
                {steps} kill-chain step{steps === 1 ? '' : 's'}
              </span>
            )}
            {sourceIp && (
              <span className="rounded-md border border-base-700 bg-base-950 px-2 py-1 font-mono text-[11px] text-base-400">
                src {sourceIp}
              </span>
            )}
          </div>

          {techniques.length > 0 && (
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-base-500">MITRE ATT&CK</p>
              <div className="flex flex-wrap gap-1.5">
                {techniques.map((t) => (
                  <span
                    key={safeString(t)}
                    className="rounded border border-base-600 bg-base-950 px-2 py-0.5 font-mono text-[11px] text-base-200"
                  >
                    {safeString(t)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex w-full shrink-0 flex-col gap-2 sm:w-auto sm:min-w-[200px]">
          <button
            type="button"
            onClick={onBlockIp}
            className="flex items-center justify-center gap-2 rounded-lg border border-base-700 bg-base-950 px-4 py-2.5 text-sm font-medium text-base-200 transition-colors duration-200 hover:border-base-600 hover:bg-base-900"
          >
            <Ban className="h-4 w-4 text-base-400" />
            Block IP
          </button>
          <button
            type="button"
            onClick={onOpenIncident}
            className="flex items-center justify-center gap-2 rounded-lg border border-base-700 bg-base-950 px-4 py-2.5 text-sm font-medium text-base-200 transition-colors hover:border-base-500 hover:bg-base-900"
          >
            <FolderOpen className="h-4 w-4 text-base-400" />
            Open incident
          </button>
          <button
            type="button"
            onClick={onAssign}
            className="flex items-center justify-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-medium text-base-100 transition-colors hover:bg-accent/20"
          >
            <UserPlus className="h-4 w-4 text-accent" />
            Assign
          </button>
        </div>
      </div>
    </section>
  );
}
