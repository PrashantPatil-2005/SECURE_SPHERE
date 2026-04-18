import { threatLevelColor, cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { edgesForNode } from '@/components/topology/layerUtils';
import TopologyChecklist from '@/components/TopologyChecklist';

const LEGEND = [
  { label: 'Normal', level: 'normal' },
  { label: 'Suspicious', level: 'suspicious' },
  { label: 'Threatening', level: 'threatening' },
  { label: 'Critical', level: 'critical' },
];

function SectionTitle({ children, className }) {
  return (
    <h4
      className={cn(
        'border-b border-dashed border-white/[0.08] pb-1.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-base-500',
        className
      )}
    >
      {children}
    </h4>
  );
}

/**
 * Right rail: legend, selected service, actions, topology checks.
 */
export default function TopologySidebar({
  topology = { nodes: [], edges: [] },
  riskScores = {},
  selectedNode,
  onClearSelection,
}) {
  const edges = topology.edges || [];
  const { inEdges, outEdges } = selectedNode
    ? edgesForNode(selectedNode.id, edges)
    : { inEdges: [], outEdges: [] };

  const rs = selectedNode ? riskScores[selectedNode.id] : null;
  const eventsPerMin = selectedNode
    ? ((selectedNode.events_count || 0) / Math.max(1, 5)).toFixed(1)
    : null;
  const mitreTags = rs?.top_events?.length
    ? rs.top_events.slice(0, 4)
    : ['T1190', 'T1078', 'T1021'];

  return (
    <aside className="flex min-h-0 w-full min-w-0 flex-col gap-3 overflow-y-auto lg:max-w-[220px]">
      <div className="rounded-lg border border-dashed border-white/[0.08] bg-base-950/40 p-3">
        <SectionTitle>Legend</SectionTitle>
        <ul className="mt-2.5 flex flex-col gap-2">
          {LEGEND.map((l) => (
            <li key={l.level} className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full border border-white/10"
                style={{
                  borderColor: threatLevelColor(l.level),
                  background: `${threatLevelColor(l.level)}22`,
                }}
              />
              <span className="text-[11px] text-base-400">{l.label}</span>
            </li>
          ))}
        </ul>
        <div className="my-2.5 h-px bg-white/[0.06]" />
        <div className="flex items-center gap-2">
          <div className="h-0 w-6 border-t-2 border-dashed border-red-500/90" />
          <span className="text-[11px] text-base-400">Attack path</span>
        </div>
        <div className="mt-1.5 flex items-center gap-2">
          <div className="h-0 w-6 border-t border-white/10" />
          <span className="text-[11px] text-base-400">Dependency</span>
        </div>
      </div>

      <div className="rounded-lg border border-dashed border-white/[0.08] bg-base-950/40 p-3">
        <SectionTitle>Selected node</SectionTitle>
        {!selectedNode ? (
          <p className="mt-2 text-[11px] leading-relaxed text-base-600">
            Click a service in the graph or layered view to inspect dependencies, risk, and signals.
          </p>
        ) : (
          <div className="mt-2.5 space-y-2 font-mono text-[10px] text-base-400">
            <div>
              <span className="text-base-600">Service</span>
              <div className="mt-0.5 text-[12px] font-semibold text-base-200">{selectedNode.name}</div>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-base-600">Risk score</span>
              <span style={{ color: threatLevelColor(selectedNode.level) }} className="tabular-nums font-semibold">
                {Math.round(selectedNode.risk ?? rs?.current_score ?? 0)}
              </span>
            </div>
            <div>
              <span className="text-base-600">Inbound</span>
              <div className="mt-0.5 break-all text-base-300">{inEdges.length ? inEdges.join(', ') : '—'}</div>
            </div>
            <div>
              <span className="text-base-600">Outbound</span>
              <div className="mt-0.5 break-all text-base-300">{outEdges.length ? outEdges.join(', ') : '—'}</div>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-base-600">Events / min (est.)</span>
              <span className="tabular-nums text-base-300">{eventsPerMin}</span>
            </div>
            <div>
              <span className="text-base-600">MITRE patterns</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {mitreTags.map((t) => (
                  <span
                    key={t}
                    className="rounded border border-white/[0.08] bg-base-900/80 px-1.5 py-0.5 text-[9px] text-base-400"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <Button variant="secondary" size="sm" className="mt-1 w-full text-[10px]" onClick={onClearSelection}>
              Clear selection
            </Button>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-dashed border-white/[0.08] bg-base-950/40 p-3">
        <SectionTitle>Actions</SectionTitle>
        <div className="mt-2.5 flex flex-col gap-1.5">
          <Button
            variant="secondary"
            size="sm"
            className="w-full justify-center text-[10px]"
            disabled={!selectedNode}
            onClick={() =>
              selectedNode && window.alert(`Isolate ${selectedNode.id} — wire to policy engine / mesh (stub).`)
            }
          >
            Isolate
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="w-full justify-center text-[10px]"
            disabled={!selectedNode}
            onClick={() =>
              selectedNode && window.alert(`View logs: ${selectedNode.id} — deep link to SIEM (stub).`)
            }
          >
            View logs
          </Button>
        </div>
      </div>

      <div className="min-w-0">
        <SectionTitle className="mb-2">System checks</SectionTitle>
        <TopologyChecklist />
      </div>
    </aside>
  );
}
