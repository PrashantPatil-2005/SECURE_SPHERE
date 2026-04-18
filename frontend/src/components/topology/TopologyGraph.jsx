import { useRef, useEffect, useState, useLayoutEffect } from 'react';
import * as d3 from 'd3';
import { threatLevelColor } from '@/lib/utils';

function linkKey(d) {
  const s = d.source?.id ?? d.source;
  const t = d.target?.id ?? d.target;
  return `${s}->${t}`;
}

/**
 * Variant A — D3 force-directed graph (preserves existing simulation, zoom, attack path).
 * Selection + hover edge emphasis via D3 (no sim restart on hover).
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
  const onNodeSelectRef = useRef(onNodeSelect);
  onNodeSelectRef.current = onNodeSelect;
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    const { nodes, edges } = topology;
    if (!nodes.length) return;

    const width = containerRef.current.clientWidth || 400;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    linkSelectionRef.current = null;

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
    enriched.forEach((n) => {
      nodeMap[n.id] = n;
    });

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

    const attackPathSet = new Set();
    if (attackPath?.length) {
      for (let i = 0; i < attackPath.length - 1; i++) {
        attackPathSet.add(`${attackPath[i]}->${attackPath[i + 1]}`);
      }
    }

    const link = g
      .append('g')
      .attr('class', 'topology-links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', (d) => {
        const key = linkKey(d);
        return attackPathSet.has(key) ? '#ef4444' : 'rgba(255,255,255,0.08)';
      })
      .attr('stroke-width', (d) => (attackPathSet.has(linkKey(d)) ? 2.5 : 1))
      .attr('stroke-dasharray', (d) => (attackPathSet.has(linkKey(d)) ? '6 4' : ''))
      .attr('opacity', 1);

    linkSelectionRef.current = link;

    if (attackPath?.length) {
      link
        .filter((d) => attackPathSet.has(linkKey(d)))
        .attr('stroke-dashoffset', 0)
        .transition()
        .duration(1000)
        .ease(d3.easeLinear)
        .attrTween('stroke-dashoffset', () => d3.interpolate(0, -20))
        .on('end', function repeat() {
          d3.select(this)
            .attr('stroke-dashoffset', 0)
            .transition()
            .duration(1000)
            .ease(d3.easeLinear)
            .attrTween('stroke-dashoffset', () => d3.interpolate(0, -20))
            .on('end', repeat);
        });
    }

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

    node
      .filter((d) => d.risk > 70)
      .append('circle')
      .attr('r', 22)
      .attr('fill', 'none')
      .attr('stroke', (d) => threatLevelColor(d.level))
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.3);

    node
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
      linkSelectionRef.current = null;
    };
  }, [topology, riskScores, height, attackPath]);

  useLayoutEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg
      .selectAll('g.node-group')
      .select('circle.main-node')
      .attr('stroke-width', function () {
        const id = d3.select(this.parentNode).attr('data-node-id');
        return id === selectedNodeId ? 3 : 2;
      });
  }, [selectedNodeId, topology]);

  return (
    <div ref={containerRef} className={`relative w-full min-w-0 ${className}`} style={{ height }}>
      <svg ref={svgRef} width="100%" height={height} className="bg-transparent" />
      {tooltip && (
        <div
          className="pointer-events-none absolute z-50 rounded-md border border-white/10 bg-base-900/95 px-3 py-2 backdrop-blur-sm"
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
