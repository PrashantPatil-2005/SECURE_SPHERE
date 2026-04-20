import { cn } from '@/lib/utils';
import { threatLevelColor } from '@/lib/utils';

/**
 * Service card for layered topology (Variant B).
 */
export default function ServiceNode({ node, selected, onSelect }) {
  const color = threatLevelColor(node.level);
  return (
    <button
      type="button"
      onClick={() => onSelect?.(node)}
      className={cn(
        'group flex w-full flex-col gap-1 rounded-md border border-dashed px-2.5 py-2 text-left transition-all duration-200 ease-out',
        'border-base-800 bg-base-950/40 hover:-translate-y-0.5 hover:bg-base-900/60',
        selected && 'ring-1 ring-offset-0'
      )}
      style={selected ? { borderColor: color, boxShadow: `0 0 0 1px ${color}55, 0 4px 18px -6px ${color}66` } : undefined}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full transition-transform duration-200 group-hover:scale-125"
          style={{
            backgroundColor: color,
            boxShadow: `0 0 0 2px ${color}22, 0 0 8px ${color}66`,
          }}
        />
        <span className="truncate font-mono text-[11px] font-semibold text-base-200 group-hover:text-base-100">{node.name || node.id}</span>
      </div>
      <div className="flex items-center justify-between gap-2 font-mono text-[10px] text-base-500">
        <span>Risk</span>
        <span className="tabular-nums font-bold" style={{ color }}>
          {Math.round(node.risk ?? 0)}
        </span>
      </div>
    </button>
  );
}
