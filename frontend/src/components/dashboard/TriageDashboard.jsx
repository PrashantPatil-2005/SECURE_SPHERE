import EventsAreaChart from '@/components/charts/EventsAreaChart';
import AlertReductionCard from './AlertReductionCard';
import ChartCard from './ChartCard';
import IncidentList from './IncidentList';
import KPIBar from './KPIBar';
import LiveFeed from './LiveFeed';
import ServiceTopologyCard from './ServiceTopologyCard';

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
  return (
    <div className="space-y-4">
      <KPIBar items={kpiItems} />
      <AlertReductionCard metrics={metrics} />

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
        <div className="xl:col-span-5">
          <LiveFeed events={events} />
        </div>
      </div>
    </div>
  );
}
