import EventsAreaChart from '@/components/charts/EventsAreaChart';
import ThreatDonutChart from '@/components/charts/ThreatDonutChart';
import TopServicesBar from '@/components/charts/TopServicesBar';
import ChartCard from './ChartCard';
import IncidentList from './IncidentList';
import KPIBar from './KPIBar';
import LiveFeed from './LiveFeed';
import MITREPanel from './MITREPanel';
import RiskHeatmap from './RiskHeatmap';

/**
 * Variant B — balanced monitoring wall.
 */
export default function GridDashboard({
  kpiItems,
  events,
  incidents,
  timeline,
  riskScores,
  selectedId,
  onSelectIncident,
}) {
  return (
    <div className="space-y-4">
      <KPIBar items={kpiItems} columnsClassName="grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard
          title="Events over time"
          className="lg:col-span-2"
          bodyClassName="pt-2"
        >
          {timeline.length > 0 ? (
            <EventsAreaChart data={timeline} />
          ) : (
            <div className="flex h-[200px] items-center justify-center text-xs text-base-500">No timeline data</div>
          )}
        </ChartCard>

        <ChartCard title="Threat distribution" bodyClassName="flex min-h-[200px] items-center justify-center pt-2">
          <ThreatDonutChart events={events} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RiskHeatmap riskScores={riskScores} />
        <ChartCard title="Top attacked services" bodyClassName="pt-0">
          <TopServicesBar events={events} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <LiveFeed events={events} maxItems={20} />
        <IncidentList incidents={incidents} maxItems={6} selectedId={selectedId} onSelect={onSelectIncident} />
      </div>

      <MITREPanel />
    </div>
  );
}
