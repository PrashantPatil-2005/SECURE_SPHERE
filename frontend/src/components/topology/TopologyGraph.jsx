import { useRef, useEffect, useState, useLayoutEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { Play, Square } from 'lucide-react';
import { threatLevelColor } from '@/lib/utils';

const ATTACK_RED = '#ef4444';
const STEP_MS = 800;
const EDGE_DRAW_MS = 600;

function linkKey(d) {
  const s = d.source?.id ?? d.source;
  const t = d.target?.id ?? d.target;
  return `${s}->${t}`;
}

/**
 * Variant A — D3 force-directed graph with kill-chain replay animation.
 * When `attackPath` transitions from empty to non-empty, the graph auto-plays
 * the attack step-by-step: highlight node, draw animated red edge, next node.
 */
export default function TopologyGraph({
  topology = { nodes: [], edges: [] },
  riskScores = {},
  height = 500,
  attackPath,
  selectedNodeId,
  onNodeSelect,
  className = '',
}) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const linkSelectionRef = useRef(null);
  const nodesByIdRef = useRef(new Map());     // id -> { group, mainCircle, ring, enriched }
  const linksByKeyRef = useRef(new Map());    // "s->t" -> line selection
  const onNodeSelectRef = useRef(onNodeSelect);
  onNodeSelectRef.current = onNodeSelect;

  // Animation state isolated in a ref so scheduled steps don't cause re-renders.
  const animRef = useRef({ timeouts: [], step: 0, active: false });

  const [tooltip, setTooltip] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

  const hasPath = Array.isArray(attackPath) && attackPath.length > 0;
  const pathKey = hasPath ? attackPath.join('>') : '';

  // Reset every highlighted node/edge back to baseline.
  const resetVisuals = useCallback(() => {
    const linkMap = linksByKeyRef.current;
    linkMap.forEach((sel) => {
      sel.interrupt()
        .attr('stroke', 'rgba(255,255,255,0.08)')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', null)
        .attr('stroke-dashoffset', null)
        .attr('opacity', 1);
    });

    const nodeMap = nodesByIdRef.current;
    nodeMap.forEach(({ mainCircle, ring, level }) => {
      if (!mainCircle) return;
      mainCircle.interrupt()
        .attr('stroke', threatLevelColor(level))
        .attr('stroke-width', 2)
        .classed('attack-node-pulse', false);
      if (ring) ring.style('opacity', 0);
    });
  }, []);

  const clearTimeouts = useCallback(() => {
    animRef.current.timeouts.forEach(clearTimeout);
    animRef.current.timeouts = [];
  }, []);

  const highlightNode = useCallback((nodeId) => {
    const entry = nodesByIdRef.current.get(nodeId);
    if (!entry) return;
    entry.mainCircle
      .interrupt()
      .attr('stroke', ATTACK_RED)
      .attr('stroke-width', 3)
      .classed('attack-node-pulse', true);
    if (entry.ring) {
      entry.ring
        .attr('stroke', ATTACK_RED)
        .style('opacity', 1)
        .classed('attack-ring-pulse', true);
    }
  }, []);

  const animateEdge = useCallback((fromId, toId) => {
    const sel = linksByKeyRef.current.get(`${fromId}->${toId}`)
      || linksByKeyRef.current.get(`${toId}->${fromId}`);
    if (!sel) return;
    const dashLen = 10;
    sel.interrupt()
      .attr('stroke', ATTACK_RED)
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', `${dashLen} ${dashLen}`)
      .attr('stroke-dashoffset', dashLen * 8)
      .transition()
      .duration(EDGE_DRAW_MS)
      .ease(d3.easeLinear)
      .attr('stroke-dashoffset', 0)
      .on('end', function flow() {
        d3.select(this)
          .attr('stroke-dashoffset', dashLen * 2)
          .transition()
          .duration(1000)
          .ease(d3.easeLinear)
          .attr('stroke-dashoffset', 0)
          .on('end', flow);
      });
  }, []);

  const stopReplay = useCallback(() => {
    clearTimeouts();
    animRef.current.active = false;
    animRef.current.step = 0;
    resetVisuals();
    setPlaying(false);
    setShowLegend(false);
  }, [clearTimeouts, resetVisuals]);

  const playReplay = useCallback(() => {
    if (!hasPath) return;
    clearTimeouts();
    resetVisuals();
    animRef.current.active = true;
    animRef.current.step = 0;
    setPlaying(true);
    setShowLegend(false);

    const sched = (delay, fn) => {
      const id = setTimeout(fn, delay);
      animRef.current.timeouts.push(id);
    };

    // Step 1+: for hop i, at delay = (i*2+1)*STEP_MS highlight node[i];
    // then at (i*2+2)*STEP_MS animate edge[i-1 → i] (i>=1).
    attackPath.forEach((nodeId, i) => {
      const nodeDelay = (i * 2 + 1) * STEP_MS;
      sched(nodeDelay, () => highlightNode(nodeId));
      if (i > 0) {
        const edgeDelay = (i * 2) * STEP_MS;
        sched(edgeDelay, () => animateEdge(attackPath[i - 1], nodeId));
      }
    });

    const finalDelay = (attackPath.length * 2 + 1) * STEP_MS;
    sched(finalDelay, () => {
      animRef.current.active = false;
      setPlaying(false);
      setShowLegend(true);
    });
  }, [attackPath, hasPath, clearTimeouts, resetVisuals, highlightNode, animateEdge]);

  // Build / rebuild the D3 graph.
  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    const { nodes, edges } = topology;
    if (!nodes.length) return;

    const width = containerRef.current.clientWidth || 400;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    linkSelectionRef.current = null;
    linksByKeyRef.current = new Map();
    nodesByIdRef.current = new Map();

    const g = svg.append('g');

    const zoom = d3.zoom().scaleExtent([0.3, 3]).on('zoom', (e) => g.attr('transform', e.transform));
    svg.call(zoom);
    svg.on('click', () => onNodeSelectRef.current?.(null));

    const enriched = nodes.map((n) => ({
      ...n,
      risk: riskScores[n.id]?.current_score || n.risk_score || 0,
      level: riskScores[n.id]?.threat_level || 'normal',
    }));

    const nodeMap = {};
    enriched.forEach((n) => { nodeMap[n.id] = n; });

    const links = edges
      .filter((e) => nodeMap[e.source] || nodeMap[e.source?.id])
      .map((e) => ({
        source: typeof e.source === 'string' ? e.source : e.source.id,
        target: typeof e.target === 'string' ? e.target : e.target.id,
      }));

    const sim = d3
      .forceSimulation(enriched)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(40));

    const link = g
      .append('g')
      .attr('class', 'topology-links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'rgba(255,255,255,0.08)')
      .attr('stroke-width', 1)
      .attr('opacity', 1);

    linkSelectionRef.current = link;
    link.each(function (d) {
      linksByKeyRef.current.set(linkKey(d), d3.select(this));
    });

    const setLinkHighlight = (nodeId) => {
      if (!linkSelectionRef.current) return;
      linkSelectionRef.current.attr('opacity', (d) => {
        if (!nodeId) return 1;
        const s = d.source.id ?? d.source;
        const t = d.target.id ?? d.target;
        return s === nodeId || t === nodeId ? 1 : 0.12;
      });
    };

    const node = g
      .append('g')
      .selectAll('g')
      .data(enriched)
      .join('g')
      .attr('class', 'node-group')
      .attr('data-node-id', (d) => d.id)
      .call(
        d3
          .drag()
          .on('start', (e, d) => {
            if (!e.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (e, d) => {
            d.fx = e.x;
            d.fy = e.y;
          })
          .on('end', (e, d) => {
            if (!e.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    // Outer ring (always created for attack-path pulse; hidden unless highlighted).
    const ring = node
      .append('circle')
      .attr('class', 'attack-ring')
      .attr('r', 24)
      .attr('fill', 'none')
      .attr('stroke', ATTACK_RED)
      .attr('stroke-width', 2)
      .style('opacity', 0)
      .style('pointer-events', 'none');

    // High-risk static ring
    node
      .filter((d) => d.risk > 70)
      .append('circle')
      .attr('r', 22)
      .attr('fill', 'none')
      .attr('stroke', (d) => threatLevelColor(d.level))
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.3);

    const mainCircle = node
      .append('circle')
      .attr('class', 'main-node')
      .attr('r', 16)
      .attr('fill', '#0d1117')
      .attr('stroke', (d) => threatLevelColor(d.level))
      .attr('stroke-width', (d) => (selectedNodeId === d.id ? 3 : 2))
      .style('cursor', 'pointer')
      .on('mouseenter', (e, d) => {
        e.stopPropagation();
        setLinkHighlight(d.id);
        const rect = containerRef.current.getBoundingClientRect();
        setTooltip({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top - 10,
          data: d,
        });
      })
      .on('mouseleave', () => {
        setLinkHighlight(null);
        setTooltip(null);
      })
      .on('click', (e, d) => {
        e.stopPropagation();
        onNodeSelectRef.current?.(d);
      });

    // Populate node map for animation lookups.
    node.each(function (d) {
      const group = d3.select(this);
      nodesByIdRef.current.set(d.id, {
        group,
        mainCircle: group.select('circle.main-node'),
        ring: group.select('circle.attack-ring'),
        level: d.level,
      });
    });

    node
      .append('text')
      .text((d) => d.name?.replace('-service', '').slice(0, 4).toUpperCase())
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', (d) => threatLevelColor(d.level))
      .attr('font-size', 8)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-weight', 600)
      .style('pointer-events', 'none');

    node
      .append('text')
      .text((d) => d.name)
      .attr('text-anchor', 'middle')
      .attr('dy', 28)
      .attr('fill', '#94a3b8')
      .attr('font-size', 9)
      .attr('font-family', 'Inter, sans-serif')
      .style('pointer-events', 'none');

    sim.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);
      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    return () => {
      sim.stop();
      clearTimeouts();
      linkSelectionRef.current = null;
      linksByKeyRef.current = new Map();
      nodesByIdRef.current = new Map();
    };
  }, [topology, riskScores, height, clearTimeouts]);

  // Auto-play replay whenever attackPath transitions to a non-empty chain.
  useEffect(() => {
    if (!hasPath) {
      stopReplay();
      return;
    }
    // Let D3 finish its first sim tick before triggering animation.
    const id = setTimeout(() => playReplay(), 50);
    return () => {
      clearTimeout(id);
      clearTimeouts();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathKey, hasPath]);

  useLayoutEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg
      .selectAll('g.node-group')
      .select('circle.main-node')
      .attr('stroke-width', function () {
        const id = d3.select(this.parentNode).attr('data-node-id');
        // Don't override a replay highlight.
        const entry = nodesByIdRef.current.get(id);
        const isAttackNode = entry && attackPath?.includes(id);
        if (isAttackNode) return 3;
        return id === selectedNodeId ? 3 : 2;
      });
  }, [selectedNodeId, topology, attackPath]);

  return (
    <div ref={containerRef} className={`relative w-full min-w-0 ${className}`} style={{ height }}>
      {/* Scoped CSS for pulse animations */}
      <style>{`
        @keyframes attackNodePulse {
          0%, 100% { stroke-width: 3; filter: drop-shadow(0 0 2px ${ATTACK_RED}); }
          50%      { stroke-width: 4; filter: drop-shadow(0 0 10px ${ATTACK_RED}); }
        }
        .attack-node-pulse { animation: attackNodePulse 1.2s ease-in-out infinite; }
        @keyframes attackRingPulse {
          0%   { r: 20; opacity: 0.9; }
          100% { r: 34; opacity: 0;   }
        }
        .attack-ring-pulse { animation: attackRingPulse 1.4s ease-out infinite; transform-origin: center; }
      `}</style>

      <svg ref={svgRef} width="100%" height={height} className="bg-transparent" />

      {/* Replay / Reset overlay */}
      {hasPath && (
        <div className="absolute top-2 right-2 flex items-center gap-1.5 z-20">
          <button
            type="button"
            onClick={playReplay}
            disabled={playing}
            className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md text-[11px] font-semibold uppercase tracking-wider border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Replay attack path"
          >
            <Play className="w-3 h-3" fill="currentColor" />
            {playing ? 'Replaying…' : 'Replay'}
          </button>
          <button
            type="button"
            onClick={stopReplay}
            className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md text-[11px] font-semibold uppercase tracking-wider border border-base-700 bg-base-900/80 text-base-300 hover:bg-base-800 transition-colors"
            title="Reset animation"
          >
            <Square className="w-3 h-3" fill="currentColor" />
            Reset
          </button>
        </div>
      )}

      {/* Attack path legend (bottom-left) */}
      {showLegend && (
        <div className="absolute bottom-2 left-2 z-20 inline-flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-red-500/30 bg-red-500/10 backdrop-blur-sm">
          <span className="inline-flex h-2 w-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-red-300">
            Attack Path
          </span>
          <span className="text-[10px] font-mono text-red-300/70">
            {attackPath.length} hops
          </span>
        </div>
      )}

      {tooltip && (
        <div
          className="pointer-events-none absolute z-50 rounded-md border border-base-800 bg-base-900/95 px-3 py-2 backdrop-blur-sm"
          style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, -100%)' }}
        >
          <div className="mb-1 text-xs font-semibold text-base-100">{tooltip.data.name}</div>
          <div className="space-y-0.5 text-[10px] text-base-400">
            <div>
              Risk:{' '}
              <span className="font-mono font-semibold" style={{ color: threatLevelColor(tooltip.data.level) }}>
                {tooltip.data.risk}
              </span>
            </div>
            <div>Status: {tooltip.data.status || 'running'}</div>
            <div>Events: {tooltip.data.events_count || 0}</div>
          </div>
        </div>
      )}
    </div>
  );
}
