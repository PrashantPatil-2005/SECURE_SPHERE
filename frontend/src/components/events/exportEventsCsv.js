import { getSeverityString, safeString } from '@/lib/utils';

/**
 * @param {Record<string, unknown>[]} filtered
 */
export function exportEventsCsv(filtered) {
  const header = 'timestamp,event_type,severity,source_ip,source_service,layer,mitre\n';
  const rows = filtered
    .map(
      (ev) =>
        `${ev.timestamp},${safeString(ev.event_type)},${getSeverityString(ev.severity)},${ev.source_entity?.ip ?? ''},${ev.source_entity?.service ?? ''},${safeString(ev.source_layer)},${safeString(ev.mitre_technique) || ''}`
    )
    .join('\n');
  const blob = new Blob([header + rows], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `securisphere-events-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
