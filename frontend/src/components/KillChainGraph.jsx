import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';

/**
 * D3 force-directed kill chain graph from backend `graph` JSONB.
 */
export default function KillChainGraph({ graph, className }) {
  const svgRef = useRef(null);

  useEffect(() => {
    const nodes = graph?.nodes || [];
    const edges = graph?.edges || [];
    if (!svgRef.current || nodes.length === 0) return;

    const width = 480;
    const height = 220;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const simNodes = nodes.map((n) => ({ ...n, id: n.id || n.label }));
    const simLinks = edges.map((e) => ({
      source: e.source,
      target: e.target,
    }));

    const simulation = d3
      .forceSimulation(simNodes)
      .force('link', d3.forceLink(simLinks).id((d) => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg
      .append('g')
      .selectAll('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', 'var(--base-500)')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)');

    svg
      .append('defs')
      .append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'var(--base-500)');

    const node = svg
      .append('g')
      .selectAll('g')
      .data(simNodes)
      .join('g');

    node
      .append('circle')
      .attr('r', 14)
      .attr('fill', 'var(--base-800)')
      .attr('stroke', 'var(--accent)')
      .attr('stroke-width', 1.5);

    node
      .append('text')
      .text((d) => d.label || d.id)
      .attr('text-anchor', 'middle')
      .attr('dy', 28)
      .attr('class', 'fill-base-400 text-2xs font-mono');

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);
      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [graph]);

  if (!graph?.nodes?.length) return null;

  return (
    <svg
      ref={svgRef}
      className={cn('w-full h-[220px]', className)}
      role="img"
      aria-label="Kill chain service graph"
    />
  );
}
