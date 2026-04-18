import Chip from '@/components/intro/Chip';
import SeverityDot from '@/components/intro/SeverityDot';
import Tag from '@/components/intro/Tag';

/**
 * Typography + color primitives for the SOC console.
 */
export default function DesignSystem() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-base-500">Typography</h3>
        <dl className="space-y-2 text-sm">
          <div className="flex flex-wrap items-baseline gap-2">
            <dt className="w-24 shrink-0 font-mono text-[10px] text-base-600">Display</dt>
            <dd className="text-2xl font-semibold tracking-tight text-base-100">SecuriSphere</dd>
          </div>
          <div className="flex flex-wrap items-baseline gap-2">
            <dt className="w-24 shrink-0 font-mono text-[10px] text-base-600">Body</dt>
            <dd className="max-w-prose text-base-300">
              Inter — readable body copy for analyst notes, tables, and dense SOC layouts.
            </dd>
          </div>
          <div className="flex flex-wrap items-baseline gap-2">
            <dt className="w-24 shrink-0 font-mono text-[10px] text-base-600">Mono</dt>
            <dd className="font-mono text-xs text-base-400">10.0.2.4 · inc_0c1f · severity:critical · T1190</dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-base-500">Colors — severity</h3>
        <div className="flex flex-wrap gap-2">
          <Chip variant="critical">critical</Chip>
          <Chip variant="high">high</Chip>
          <Chip variant="medium">medium</Chip>
          <Chip variant="low">low</Chip>
          <Chip variant="info">info</Chip>
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-base-500">Status & layers</h3>
        <div className="flex flex-wrap items-center gap-3 text-xs text-base-400">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-base-400 shadow-[0_0_6px_rgba(0,0,0,0.12)] dark:shadow-[0_0_8px_rgba(255,255,255,0.1)]" />
            Live
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-base-500" />
            Attention
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-base-300" />
            UI focus
          </span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-mono uppercase tracking-wider text-base-600">Primitives</span>
          <SeverityDot level="critical" />
          <SeverityDot level="high" />
          <SeverityDot level="medium" />
          <Tag label="network" />
          <Tag label="api" />
          <Tag label="auth" />
        </div>
      </div>
    </div>
  );
}
