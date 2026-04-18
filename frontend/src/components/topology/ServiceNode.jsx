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
        'flex w-full flex-col gap-1 rounded-md border border-dashed px-2.5 py-2 text-left transition-colors',
        'border-base-800 bg-base-950/40 hover:border-accent/25 hover:bg-base-900/60',
        selected && 'border-accent/40 bg-accent/[0.08] ring-1 ring-accent/20'
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2 w-2 shrink-0 rounded-full border border-base-800"
          style={{ backgroundColor: `${color}99`, boxShadow: `0 0 0 1px ${color}44` }}
        />
        <span className="truncate font-mono text-[11px] font-semibold text-base-200">{node.name || node.id}</span>
      </div>
      <div className="flex items-center justify-between gap-2 font-mono text-[10px] text-base-500">
        <span>Risk</span>
        <span className="tabular-nums" style={{ color }}>
          {Math.round(node.risk ?? 0)}
        </span>
      </div>
    </button>
  );
}
