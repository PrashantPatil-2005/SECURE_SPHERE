import { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Network } from 'lucide-react';
import { Select } from '@/components/ui/input';
import TopologyGraph from '@/components/topology/TopologyGraph';
import TopologyLayers from '@/components/topology/TopologyLayers';
import TopologySidebar from '@/components/topology/TopologySidebar';
import { enrichNodesWithLayer } from '@/components/topology/layerUtils';
import { cn } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

const GRAPH_H = 520;

/**
 * Production topology shell: left controls, center visualization, right SOC sidebar.
 */
export default function TopologyPage({ topology, riskScores, incidents }) {
  const [viewMode, setViewMode] = useState('graph');
  const [selectedIncident, setSelectedIncident] = useState('none');
  const [selectedNode, setSelectedNode] = useState(null);

  const attackPath =
    selectedIncident !== 'none'
      ? incidents.find((i) => i.incident_id === selectedIncident)?.service_path || []
      : [];

  const enrichedIndex = useMemo(() => {
    const list = enrichNodesWithLayer(topology.nodes || [], riskScores);
    const m = {};
    list.forEach((n) => {
      m[n.id] = n;
    });
    return m;
  }, [topology.nodes, riskScores]);

  const handleSelectNode = useCallback(
    (raw) => {
      if (!raw) {
        setSelectedNode(null);
        return;
      }
      setSelectedNode(enrichedIndex[raw.id] || raw);
    },
    [enrichedIndex]
  );

  const hasData = (topology.nodes?.length || 0) > 0;

  return (
    <motion.div {...anim} className="flex min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-base-100">Service topology</h2>
          <p className="mt-0.5 font-mono text-[11px] text-base-500">
            {topology.nodes?.length || 0} nodes · {topology.edges?.length || 0} edges
          </p>
        </div>
        <label className="flex flex-col gap-1 font-mono text-[10px] text-base-500">
          <span>Overlay attack path</span>
          <Select
            value={selectedIncident}
            onChange={(e) => setSelectedIncident(e.target.value)}
            className="h-9 min-w-[200px] text-xs"
          >
            <option value="none">None</option>
            {incidents.map((inc) => (
              <option key={inc.incident_id} value={inc.incident_id}>
                {inc.title?.slice(0, 42) || inc.incident_id}
              </option>
            ))}
          </Select>
        </label>
      </div>

      <div
        className={cn(
          'grid min-h-0 min-w-0 flex-1 gap-3',
          'grid-cols-1 lg:grid-cols-[130px_minmax(0,1fr)_220px]'
        )}
      >
        {/* Left rail — view mode (not global SidebarNav) */}
        <div className="flex flex-col gap-2 rounded-lg border border-dashed border-white/[0.08] bg-base-950/40 p-2.5 lg:min-h-[520px]">
          <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-base-600">
            View
          </span>
          <div className="flex flex-col gap-1">
            <button
              type="button"
              onClick={() => setViewMode('graph')}
              className={cn(
                'rounded-md border border-dashed px-2 py-2 text-left font-mono text-[11px] transition-colors',
                viewMode === 'graph'
                  ? 'border-accent/35 bg-accent/[0.1] text-accent'
                  : 'border-white/[0.06] text-base-400 hover:border-white/[0.1]'
              )}
            >
              Graph
            </button>
            <button
              type="button"
              onClick={() => setViewMode('layered')}
              className={cn(
                'rounded-md border border-dashed px-2 py-2 text-left font-mono text-[11px] transition-colors',
                viewMode === 'layered'
                  ? 'border-accent/35 bg-accent/[0.1] text-accent'
                  : 'border-white/[0.06] text-base-400 hover:border-white/[0.1]'
              )}
            >
              Layers
            </button>
          </div>
          <p className="mt-auto hidden font-mono text-[9px] leading-snug text-base-600 lg:block">
            Drag nodes (graph). Scroll wheel zoom. Path edges pulse red when an incident is selected.
          </p>
        </div>

        {/* Center — graph or layered */}
        <div className="min-w-0 overflow-hidden rounded-lg border border-dashed border-white/[0.08] bg-base-950/30">
          {!hasData ? (
            <div className="flex h-[520px] flex-col items-center justify-center gap-2 text-sm text-base-500">
              <Network className="h-10 w-10 opacity-20" />
              <span>No topology data</span>
              <span className="max-w-xs text-center font-mono text-[10px] text-base-600">
                Start the backend collector to populate the dependency graph.
              </span>
            </div>
          ) : viewMode === 'graph' ? (
            <TopologyGraph
              topology={topology}
              riskScores={riskScores}
              height={GRAPH_H}
              attackPath={attackPath}
              selectedNodeId={selectedNode?.id}
              onNodeSelect={handleSelectNode}
            />
          ) : (
            <div className="max-h-[520px] overflow-y-auto p-3">
              <TopologyLayers
                topology={topology}
                riskScores={riskScores}
                selectedNodeId={selectedNode?.id}
                onSelectNode={handleSelectNode}
              />
            </div>
          )}
        </div>

        <TopologySidebar
          topology={topology}
          riskScores={riskScores}
          selectedNode={selectedNode}
          onClearSelection={() => setSelectedNode(null)}
        />
      </div>
    </motion.div>
  );
}
