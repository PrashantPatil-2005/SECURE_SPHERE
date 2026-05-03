import { useMemo } from 'react';
import EventsAreaChart from '@/components/charts/EventsAreaChart';
import { getSeverityString } from '@/lib/utils';
import AlertReductionCard from './AlertReductionCard';
import ChartCard from './ChartCard';
import IncidentList from './IncidentList';
import KPIBar from './KPIBar';
import LiveFeed from './LiveFeed';
import ServiceTopologyCard from './ServiceTopologyCard';
import WhatHappenedCard from './WhatHappenedCard';

/** Variant A — incident-first triage lane. */
export default function TriageDashboard({
  kpiItems,
  events,
  incidents,
  timeline,
  metrics = {},
  topology = { nodes: [], edges: [] },
  riskScores = {},
  selectedId,
  onSelectIncident,
}) {
  const featured = useMemo(() => {
    if (!incidents?.length) return null;
    if (selectedId) {
      const sel = incidents.find((i) => String(i?.incident_id ?? i?.id) === String(selectedId));
      if (sel) return sel;
    }
    return (
      incidents.find((i) => getSeverityString(i?.severity) === 'critical') || incidents[0] || null
    );
  }, [incidents, selectedId]);

  return (
    <div className="space-y-4">
      <KPIBar items={kpiItems} />
      {featured && <WhatHappenedCard incident={featured} />}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-7">
          <IncidentList
            incidents={incidents}
            maxItems={14}
            selectedId={selectedId}
            onSelect={onSelectIncident}
          />
          <ServiceTopologyCard
            topology={topology}
            riskScores={riskScores}
            incidents={incidents}
            selectedId={selectedId}
          />
          <ChartCard title="Events over time" description="Volume by severity bucket in the live window.">
            {timeline.length > 0 ? (
              <EventsAreaChart data={timeline} />
            ) : (
              <div className="flex h-[200px] items-center justify-center text-xs text-base-500">No timeline data</div>
            )}
          </ChartCard>
        </div>
        <div className="space-y-4 xl:col-span-5">
          <LiveFeed events={events} />
          <AlertReductionCard metrics={metrics} />
        </div>
      </div>
    </div>
  );
}
