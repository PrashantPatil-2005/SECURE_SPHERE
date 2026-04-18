import { cn } from '@/lib/utils';

const LAYERS = [
  { id: 'all', label: 'layer: *' },
  { id: 'network', label: 'network' },
  { id: 'api', label: 'api' },
  { id: 'auth', label: 'auth' },
  { id: 'browser', label: 'browser' },
];

const SEVS = [
  { id: 'all', label: 'sev: *' },
  { id: 'critical', label: 'crit' },
  { id: 'high', label: 'high' },
  { id: 'medium', label: 'med' },
  { id: 'low', label: 'low' },
];

const TIMES = [
  { id: 'all', label: 'time: all' },
  { id: '1h', label: '1h' },
  { id: '24h', label: '24h' },
];

const SRC = [
  { id: 'all', label: 'src: any' },
  { id: '10.0.2.4', label: 'src: 10.0.2.4' },
];

/**
 * Chip filters — compact SOC triage controls.
 *
 * @param {{
 *   layer: string;
 *   severity: string;
 *   timePreset: string;
 *   srcIp: string;
 *   onLayer: (v: string) => void;
 *   onSeverity: (v: string) => void;
 *   onTimePreset: (v: string) => void;
 *   onSrcIp: (v: string) => void;
 *   onClearTimeRange?: () => void;
 *   hasCustomTimeRange?: boolean;
 * }} props
 */
export default function EventFilters({
  layer,
  severity,
  timePreset,
  srcIp,
  onLayer,
  onSeverity,
  onTimePreset,
  onSrcIp,
  onClearTimeRange,
  hasCustomTimeRange,
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-[10px] font-mono uppercase tracking-wider text-base-600">Filters</span>
      {LAYERS.map((c) => (
        <FilterChip key={c.id} active={layer === c.id} onClick={() => onLayer(c.id)} label={c.label} />
      ))}
      <span className="text-base-700">·</span>
      {SEVS.map((c) => (
        <FilterChip key={c.id} active={severity === c.id} onClick={() => onSeverity(c.id)} label={c.label} />
      ))}
      <span className="text-base-700">·</span>
      {TIMES.map((c) => (
        <FilterChip key={c.id} active={timePreset === c.id} onClick={() => onTimePreset(c.id)} label={c.label} />
      ))}
      <span className="text-base-700">·</span>
      {SRC.map((c) => (
        <FilterChip key={c.id} active={srcIp === c.id} onClick={() => onSrcIp(c.id)} label={c.label} />
      ))}
      {hasCustomTimeRange && onClearTimeRange && (
        <button
          type="button"
          onClick={onClearTimeRange}
          className="rounded border border-base-700 bg-base-800/50 px-2 py-0.5 font-mono text-[10px] text-base-200 transition-colors duration-200 hover:bg-base-800"
        >
          clear ribbon window
        </button>
      )}
    </div>
  );
}

function FilterChip({ active, onClick, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-full border px-2 py-0.5 font-mono text-[10px] transition-colors',
        active
          ? 'border-base-600 bg-base-800 text-base-100'
          : 'border-base-800 text-base-500 hover:border-base-700 hover:text-base-400'
      )}
    >
      {label}
    </button>
  );
}
