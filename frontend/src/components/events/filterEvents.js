import { getSeverityString, safeString } from '@/lib/utils';

/**
 * @param {Record<string, unknown>[]} events
 * @param {{
 *   search: string;
 *   layer: string;
 *   severity: string;
 *   timePreset: 'all' | '1h' | '24h';
 *   srcIp: string;
 *   timeRange: { start: number; end: number } | null;
 * }} f
 */
export function filterEvents(events, f) {
  const now = Date.now();

  return events.filter((ev) => {
    const t = new Date(ev.timestamp).getTime();
    if (!Number.isFinite(t)) return false;

    if (f.timePreset === '1h') {
      if (t < now - 3600_000) return false;
    } else if (f.timePreset === '24h') {
      if (t < now - 86400_000) return false;
    }

    if (f.timeRange) {
      if (t < f.timeRange.start || t > f.timeRange.end) return false;
    }

    if (f.layer !== 'all' && safeString(ev.source_layer).toLowerCase() !== f.layer) return false;
    if (f.severity !== 'all' && getSeverityString(ev.severity) !== f.severity) return false;
    if (f.srcIp !== 'all') {
      const ip = ev.source_entity?.ip;
      if (!ip || safeString(ip) !== f.srcIp) return false;
    }
    if (f.search.trim()) {
      const q = f.search.toLowerCase();
      const searchable = `${ev.event_type} ${ev.source_entity?.ip} ${ev.source_entity?.service} ${ev.destination_entity?.service} ${ev.mitre_technique} ${ev.source_layer}`.toLowerCase();
      if (!searchable.includes(q)) return false;
    }
    return true;
  });
}
