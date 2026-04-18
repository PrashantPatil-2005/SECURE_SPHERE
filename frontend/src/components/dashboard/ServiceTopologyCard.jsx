import { useMemo } from 'react';
import { Network } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import TopologyGraph from '@/components/topology/TopologyGraph';

/**
 * Dashboard card — live service graph wired to /topology/graph, colored by
 * threat_level, with animated kill-chain overlay for the selected incident.
 */
export default function ServiceTopologyCard({
  topology = { nodes: [], edges: [] },
  riskScores = {},
  incidents = [],
  selectedId,
  height = 320,
}) {
  const attackPath = useMemo(() => {
    if (!selectedId) return [];
    const inc = incidents.find((i) => String(i?.incident_id) === String(selectedId));
    const path = inc?.service_path;
    return Array.isArray(path) ? path.filter(Boolean) : [];
  }, [incidents, selectedId]);

  const nodeCount = topology.nodes?.length || 0;
  const edgeCount = topology.edges?.length || 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col">
          <CardTitle>Service topology</CardTitle>
          <span className="mt-0.5 font-mono text-[10px] text-base-500">
            {nodeCount} nodes · {edgeCount} edges
            {attackPath.length > 0 && ` · kill-chain ${attackPath.length} hops`}
          </span>
        </div>
        <span
          className="rounded border border-base-800 bg-base-950/40 px-1.5 py-0.5 font-mono text-[10px] text-base-500"
          title="Live from /topology/graph"
        >
          live
        </span>
      </CardHeader>
      <CardContent className="p-0">
        {nodeCount === 0 ? (
          <div className="flex h-[200px] flex-col items-center justify-center gap-1 text-xs text-base-500">
            <Network className="h-8 w-8 opacity-20" />
            <span>No topology data</span>
          </div>
        ) : (
          <TopologyGraph
            topology={topology}
            riskScores={riskScores}
            height={height}
            attackPath={attackPath}
          />
        )}
      </CardContent>
    </Card>
  );
}
