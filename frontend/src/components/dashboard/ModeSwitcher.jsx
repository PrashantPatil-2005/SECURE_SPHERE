import { cn } from '@/lib/utils';

const MODES = [
  { id: 'triage', label: 'Triage', hint: 'A' },
  { id: 'grid', label: 'Grid', hint: 'B' },
  { id: 'story', label: 'Story', hint: 'C' },
];

/**
 * @param {{
 *   mode: 'triage' | 'grid' | 'story';
 *   onChange: (m: 'triage' | 'grid' | 'story') => void;
 * }} props
 */
export default function ModeSwitcher({ mode, onChange }) {
  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-lg border border-base-800 bg-base-900 p-1"
      role="tablist"
      aria-label="Dashboard layout mode"
    >
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          role="tab"
          aria-selected={mode === m.id}
          onClick={() => onChange(m.id)}
          className={cn(
            'flex items-center gap-2 rounded-md px-3 py-1.5 font-mono text-xs transition-colors',
            mode === m.id
              ? 'bg-base-950 text-base-100 ring-1 ring-base-700'
              : 'text-base-500 hover:bg-base-950/60 hover:text-base-300'
          )}
        >
          <span>{m.label}</span>
          <span className="rounded border border-base-700 px-1 text-[9px] text-base-500">{m.hint}</span>
        </button>
      ))}
    </div>
  );
}
