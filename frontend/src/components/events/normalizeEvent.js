import { getSeverityString, safeString } from '@/lib/utils';

/**
 * @param {Record<string, unknown>} ev
 * @param {number} index
 */
export function normalizeEvent(ev, index) {
  const id = ev?.event_id != null ? String(ev.event_id) : `evt-${index}`;
  const ts = ev?.timestamp ? new Date(ev.timestamp).getTime() : NaN;
  const dest = ev?.destination_entity;
  const src = ev?.source_entity?.ip || ev?.source_entity?.service;
  let target = '—';
  if (dest?.service) target = safeString(dest.service);
  else if (dest?.ip) target = safeString(dest.ip);
  else if (ev?.details && typeof ev.details === 'object' && ev.details.path) target = safeString(ev.details.path);
  else if (ev?.details && typeof ev.details === 'object' && ev.details.message) {
    target = safeString(ev.details.message).slice(0, 48);
  }

  return {
    id,
    raw: ev,
    timeMs: Number.isFinite(ts) ? ts : Date.now(),
    timeLabel: formatTimeLabel(ev?.timestamp),
    severity: getSeverityString(ev?.severity),
    layer: safeString(ev?.source_layer || 'unknown').toLowerCase(),
    event: safeString(ev?.event_type),
    service: safeString(ev?.source_entity?.service || dest?.service || '—'),
    src: src ? safeString(src) : '—',
    target,
    mitre: safeString(ev?.mitre_technique || ''),
    confidence: ev?.confidence,
  };
}

function formatTimeLabel(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  } catch {
    return '—';
  }
}
