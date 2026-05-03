import { Activity, AlertTriangle, Clock, Filter, Zap } from 'lucide-react';
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

  const openIncidents = incidents.filter((i) => String(i?.status || '').toLowerCase() === 'open');
  const resolvedIncidents = incidents.filter(
    (i) => String(i?.status || '').toLowerCase() === 'resolved'
  );
  const criticalIncidents = incidents.filter(
    (i) => getSeverityString(i?.severity) === 'critical'
  ).length;

  let reductionPct = '—';
  const corrRatio = metrics?.correlation?.compression_ratio;
  if (typeof corrRatio === 'number' && corrRatio > 0) {
    reductionPct = `${Math.min(99.9, (1 - 1 / corrRatio) * 100).toFixed(1)}%`;
  } else if (totalEvents > 0 && incidents.length > 0) {
    reductionPct = `${Math.max(0, (1 - incidents.length / totalEvents) * 100).toFixed(1)}%`;
  }

  return [
    {
      id: 'incidents',
      label: 'Active Incidents',
      value: openIncidents.length || incidents.length,
      icon: AlertTriangle,
      emphasize: criticalIncidents > 0,
      sub: `${criticalIncidents} critical`,
    },
    {
      id: 'events',
      label: 'Events (window)',
      value: totalEvents.toLocaleString(),
      icon: Activity,
      sub: events.length > 0 ? 'live feed' : 'awaiting data',
    },
    {
      id: 'mttd',
      label: 'Avg MTTD',
      value: avgMttd > 0 ? `${avgMttd}s` : '—',
      icon: Clock,
      sub: avgMttd > 0 ? 'mean time to detect' : 'awaiting data',
    },
    {
      id: 'reduction',
      label: 'Alert Reduction',
      value: reductionPct,
      icon: Filter,
      sub: 'vs raw logs',
    },
    {
      id: 'critical',
      label: 'Critical Alerts',
      value: criticalAlerts,
      icon: Zap,
      emphasize: criticalAlerts > 0,
      sub: `${events.filter((e) => getSeverityString(e?.severity) === 'high').length} high · ${resolvedIncidents.length} resolved`,
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
