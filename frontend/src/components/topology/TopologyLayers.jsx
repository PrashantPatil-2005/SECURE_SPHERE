import { enrichNodesWithLayer, groupNodesByLayer, LAYER_META, LAYER_IDS } from '@/components/topology/layerUtils';
import LayerBlock from '@/components/topology/LayerBlock';
import ServiceNode from '@/components/topology/ServiceNode';

/**
 * Variant B — layered architecture (Edge / App / Data) with service cards.
 */
export default function TopologyLayers({
  topology = { nodes: [], edges: [] },
  riskScores = {},
  selectedNodeId,
  onSelectNode,
  className = '',
}) {
  const enriched = enrichNodesWithLayer(topology.nodes || [], riskScores);
  const bands = groupNodesByLayer(enriched);

  return (
    <div className={`flex min-h-[480px] flex-col gap-3 ${className}`}>
      {bands.map(({ id, nodes }) => {
        const meta = LAYER_META[id] || { title: id, subtitle: '' };
        const highlight = id === LAYER_IDS.APP;
        return (
          <LayerBlock
            key={id}
            title={meta.title}
            subtitle={meta.subtitle}
            highlight={highlight}
            className="min-w-0"
          >
            {nodes.length === 0 ? (
              <p className="py-2 text-center font-mono text-[10px] text-base-600">No services in this tier</p>
            ) : (
              <div className="flex flex-wrap items-stretch gap-1.5">
                {nodes.map((n, i) => (
                  <div key={n.id} className="flex min-w-0 max-w-[200px] flex-1 items-center gap-1">
                    {i > 0 && (
                      <span
                        className="shrink-0 font-mono text-[10px] text-base-600"
                        aria-hidden
                      >
                        →
                      </span>
                    )}
                    <ServiceNode
                      node={n}
                      selected={selectedNodeId === n.id}
                      onSelect={onSelectNode}
                    />
                  </div>
                ))}
              </div>
            )}
          </LayerBlock>
        );
      })}

      <p className="font-mono text-[10px] leading-relaxed text-base-600">
        Arrows indicate logical east–west flow within the app tier. Edges follow live topology from the collector.
      </p>
    </div>
  );
}
