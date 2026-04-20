import { threatLevelColor, cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { edgesForNode } from '@/components/topology/layerUtils';
import TopologyChecklist from '@/components/TopologyChecklist';

const LEGEND = [
  { label: 'Normal',      level: 'normal',      range: '0–39' },
  { label: 'Suspicious',  level: 'suspicious',  range: '40–59' },
  { label: 'Threatening', level: 'threatening', range: '60–79' },
  { label: 'Critical',    level: 'critical',    range: '80+' },
];

function SectionTitle({ children, className }) {
  return (
    <h4
      className={cn(
        'border-b border-dashed border-base-800 pb-1.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-base-500',
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
      <div className="rounded-lg border border-dashed border-base-800 bg-base-950/40 p-3 transition-colors duration-200">
        <SectionTitle>Legend</SectionTitle>

        <div className="mt-2.5 text-[10px] font-mono uppercase tracking-wider text-base-600">Threat level</div>
        <ul className="mt-1.5 flex flex-col gap-1.5">
          {LEGEND.map((l) => {
            const c = threatLevelColor(l.level);
            return (
              <li key={l.level} className="flex items-center gap-2">
                <span
                  className="h-3 w-3 shrink-0 rounded-full transition-transform duration-200 hover:scale-125"
                  style={{
                    backgroundColor: c,
                    boxShadow: `0 0 0 2px ${c}22, 0 0 8px ${c}55`,
                  }}
                />
                <span className="flex-1 text-[11px]" style={{ color: c }}>{l.label}</span>
                <span className="font-mono text-[9px] tabular-nums text-base-600">{l.range}</span>
              </li>
            );
          })}
        </ul>

        <div className="my-2.5 h-px bg-gradient-to-r from-transparent via-base-700 to-transparent" />

        <div className="text-[10px] font-mono uppercase tracking-wider text-base-600">Edges</div>
        <ul className="mt-1.5 flex flex-col gap-1.5">
          <li className="flex items-center gap-2">
            <svg width="28" height="8" className="shrink-0">
              <line x1="0" y1="4" x2="28" y2="4" stroke="#a855f7" strokeWidth="1.5"
                    strokeLinecap="round" opacity="0.85"
                    style={{ filter: 'drop-shadow(0 0 3px rgba(168,85,247,0.55))' }} />
            </svg>
            <span className="text-[11px] text-base-300">Dependency</span>
          </li>
          <li className="flex items-center gap-2">
            <svg width="28" height="8" className="shrink-0">
              <line x1="0" y1="4" x2="28" y2="4" stroke="#ef4444" strokeWidth="2.5"
                    strokeDasharray="5 4" strokeLinecap="round"
                    style={{ filter: 'drop-shadow(0 0 4px rgba(239,68,68,0.7))' }}>
                <animate attributeName="stroke-dashoffset" from="9" to="0" dur="0.7s" repeatCount="indefinite" />
              </line>
            </svg>
            <span className="text-[11px] font-semibold text-red-300">Attack path</span>
          </li>
        </ul>

        <div className="my-2.5 h-px bg-gradient-to-r from-transparent via-base-700 to-transparent" />

        <div className="text-[10px] font-mono uppercase tracking-wider text-base-600">Nodes</div>
        <ul className="mt-1.5 flex flex-col gap-1.5">
          <li className="flex items-center gap-2">
            <span className="relative h-3 w-3 shrink-0">
              <span className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: '#ef4444', boxShadow: '0 0 0 2px #ef444433, 0 0 8px #ef4444aa' }} />
              <span className="absolute -inset-1 animate-ping rounded-full opacity-60"
                    style={{ boxShadow: 'inset 0 0 0 1px #ef4444' }} />
            </span>
            <span className="text-[11px] text-base-300">Under attack</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-3 w-3 shrink-0 rounded-full ring-1 ring-accent/60 ring-offset-2 ring-offset-base-950"
                  style={{ backgroundColor: 'var(--accent)' }} />
            <span className="text-[11px] text-base-300">Selected</span>
          </li>
          <li className="flex items-center gap-2">
            <span className="relative h-3 w-3 shrink-0">
              <span className="absolute inset-[-3px] rounded-full border"
                    style={{ borderColor: '#f97316', opacity: 0.5 }} />
              <span className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: '#f97316', boxShadow: '0 0 6px #f9731688' }} />
            </span>
            <span className="text-[11px] text-base-300">High-risk (&gt;70)</span>
          </li>
        </ul>
      </div>

      <div className="rounded-lg border border-dashed border-base-800 bg-base-950/40 p-3 transition-colors duration-200">
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
                    className="rounded border border-base-800 bg-base-900/80 px-1.5 py-0.5 text-[9px] text-base-400"
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

      <div className="rounded-lg border border-dashed border-base-800 bg-base-950/40 p-3 transition-colors duration-200">
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
