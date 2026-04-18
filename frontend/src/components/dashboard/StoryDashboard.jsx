import { useMemo } from 'react';
import EventsAreaChart from '@/components/charts/EventsAreaChart';
import ChartCard from './ChartCard';
import KPIBar from './KPIBar';
import LiveFeed from './LiveFeed';
import StoryHero from './StoryHero';
import { buildStorySummary } from './buildStorySummary';

/**
 * Variant C — narrative / demo lane with StoryHero as anchor.
 */
export default function StoryDashboard({
  kpiItems,
  featured,
  events,
  timeline,
  onBlockIp,
  onOpenIncident,
  onAssign,
}) {
  const summary = useMemo(() => buildStorySummary(featured), [featured]);

  return (
    <div className="space-y-4">
      <StoryHero
        incident={featured}
        summary={summary}
        onBlockIp={onBlockIp}
        onOpenIncident={onOpenIncident}
        onAssign={onAssign}
      />

      <KPIBar items={kpiItems} columnsClassName="grid-cols-2 lg:grid-cols-4" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard title="Events over time" description="Context for the featured narrative.">
          {timeline.length > 0 ? (
            <EventsAreaChart data={timeline} />
          ) : (
            <div className="flex h-[180px] items-center justify-center text-xs text-base-500">No timeline data</div>
          )}
        </ChartCard>
        <LiveFeed events={events} maxItems={18} title="Correlated feed" />
      </div>
    </div>
  );
}
