import { formatIncidentPath, killChainStepCount } from './incidentFormat';
import { getSeverityString, safeString } from '@/lib/utils';

/**
 * Plain-English blurb for Story mode (deterministic from incident fields).
 *
 * @param {Record<string, unknown> | null} incident
 */
export function buildStorySummary(incident) {
  if (!incident) return '';
  const sev = getSeverityString(incident.severity);
  const path = formatIncidentPath(incident);
  const steps = killChainStepCount(incident);
  const title = safeString(incident.title);

  const pathPhrase = path ? `Across ${path}` : 'Across your stack';
  const stepPhrase = steps > 0 ? `we count ${steps} kill-chain step${steps === 1 ? '' : 's'}` : 'the chain is still materializing';
  return `${pathPhrase}, ${title} presents as ${sev} activity — ${stepPhrase}. Prioritize containment, then validate blast radius before closing the loop.`;
}
