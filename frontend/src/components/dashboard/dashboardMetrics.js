import { Activity, AlertTriangle, Clock, Zap } from 'lucide-react';
import { getSeverityString } from '@/lib/utils';

/**
 * @param {{
 *   events: unknown[];
 *   incidents: unknown[];
 *   metrics: Record<string, unknown>;
 * }} p
 */
export function buildKpiItems({ events, incidents, metrics }) {
  const totalEvents = metrics?.raw_events?.total ?? events.length;
  const criticalAlerts = events.filter((e) => getSeverityString(e?.severity) === 'critical').length;
  const validIncidents = incidents.filter((i) => i?.mttd_seconds != null);
  const avgMttd =
    validIncidents.length > 0
      ? Math.round(
          validIncidents.reduce((sum, i) => sum + (i?.mttd_seconds || 0), 0) / validIncidents.length
        )
      : 0;

  return [
    {
      id: 'events',
      label: 'Total events',
      value: totalEvents.toLocaleString(),
      icon: Activity,
      sub: events.length > 0 ? `+${events.length} in window` : 'Awaiting data',
    },
    {
      id: 'incidents',
      label: 'Active incidents',
      value: incidents.length,
      icon: AlertTriangle,
      emphasize: incidents.length > 0,
      sub: `${incidents.filter((i) => getSeverityString(i?.severity) === 'critical').length} critical, ${incidents.filter((i) => getSeverityString(i?.severity) === 'high').length} high`,
    },
    {
      id: 'critical',
      label: 'Critical alerts',
      value: criticalAlerts,
      icon: Zap,
      emphasize: criticalAlerts > 0,
      sub: `${events.filter((e) => getSeverityString(e?.severity) === 'high').length} high, ${events.filter((e) => getSeverityString(e?.severity) === 'medium').length} medium`,
    },
    {
      id: 'mttd',
      label: 'Avg MTTD',
      value: avgMttd > 0 ? `${avgMttd}s` : '—',
      icon: Clock,
      sub: 'Mean time to detect',
    },
  ];
}

/**
 * @param {unknown[]} incidents
 */
export function pickFeaturedIncident(incidents) {
  if (!incidents?.length) return null;
  const critical = incidents.find((i) => getSeverityString(i?.severity) === 'critical');
  return critical || incidents[0];
}
