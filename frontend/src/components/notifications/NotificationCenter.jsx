import { useMemo, useState } from 'react';
import { CheckCheck, ArrowRight, Filter, Trash2, ShieldAlert } from 'lucide-react';
import { Drawer } from '@/components/ui/Drawer';
import { Button } from '@/components/ui/button';
import { cn, relativeTime, severityColor, getSeverityString } from '@/lib/utils';

const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low'];

export default function NotificationCenter({
  open,
  onClose,
  incidents = [],
  onNavigate,
  onMarkAllSeen,
  onClear,
}) {
  const [filter, setFilter] = useState('all');

  const sorted = useMemo(() => {
    const copy = [...incidents].sort(
      (a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0)
    );
    if (filter === 'all') return copy;
    return copy.filter((i) => getSeverityString(i.severity).toLowerCase() === filter);
  }, [incidents, filter]);

  const counts = useMemo(() => {
    const c = { all: incidents.length, critical: 0, high: 0, medium: 0, low: 0 };
    for (const i of incidents) {
      const s = getSeverityString(i.severity).toLowerCase();
      if (s in c) c[s] += 1;
    }
    return c;
  }, [incidents]);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      side="right"
      size="md"
      title="Notification center"
      description={`${incidents.length} active · live SOC alerts`}
      footer={
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={onMarkAllSeen}
            disabled={!incidents.length}
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium text-base-300 hover:bg-base-800 disabled:opacity-40"
          >
            <CheckCheck className="h-3.5 w-3.5" /> Mark all seen
          </button>
          <button
            type="button"
            onClick={() => {
              onClose?.();
              onNavigate?.('/incidents');
            }}
            className="inline-flex items-center gap-1.5 rounded-md bg-accent/10 px-3 py-1 text-[11px] font-semibold text-accent hover:bg-accent/15"
          >
            View all incidents <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      }
    >
      <div role="toolbar" aria-label="Severity filter" className="mb-3 flex items-center gap-1.5 overflow-x-auto pb-1">
        <Filter aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-base-500" />
        {SEVERITIES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            aria-pressed={filter === s}
            aria-label={`Filter ${s} (${counts[s] ?? 0})`}
            className={cn(
              'inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50',
              filter === s
                ? 'border-accent/40 bg-accent/10 text-accent'
                : 'border-base-800 text-base-500 hover:text-base-300'
            )}
          >
            {s}
            <span className="font-mono tabular-nums opacity-60">{counts[s] ?? 0}</span>
          </button>
        ))}
        {onClear && (
          <Button
            variant="icon"
            size="icon"
            onClick={onClear}
            title="Clear all data"
            aria-label="Clear all data"
            className="ml-auto text-base-500 hover:text-red-400"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-base-800 bg-base-900/40 px-4 py-12 text-center">
          <ShieldAlert className="h-7 w-7 text-emerald-400" />
          <p className="text-xs text-base-300">No alerts in this view</p>
          <p className="text-[11px] text-base-600">All clear. Stay frosty.</p>
        </div>
      ) : (
        <ul className="divide-y divide-dashed divide-base-800 rounded-lg border border-base-800 bg-base-900/40">
          {sorted.map((inc, i) => {
            const sev = getSeverityString(inc.severity);
            const c = severityColor(inc.severity);
            return (
              <li key={inc.incident_id || inc.id || i}>
                <button
                  type="button"
                  onClick={() => {
                    onClose?.();
                    onNavigate?.('/incidents');
                  }}
                  className="group flex w-full items-start gap-2 px-3 py-2.5 text-left transition-colors hover:bg-base-800/40"
                >
                  <span
                    className="mt-1 h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: c, boxShadow: `0 0 6px ${c}88` }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[9px] font-semibold uppercase tracking-wider"
                        style={{ color: c }}
                      >
                        {sev}
                      </span>
                      <span className="font-mono text-[9px] text-base-600">
                        {relativeTime(inc.created_at || inc.timestamp)}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-[12px] text-base-200 group-hover:text-base-100">
                      {inc.title || inc.scenario_label || inc.description || 'Incident'}
                    </p>
                    {inc.source_ip && (
                      <p className="mt-0.5 truncate font-mono text-[10px] text-base-500">
                        {inc.source_ip}
                      </p>
                    )}
                  </div>
                  <ArrowRight className="mt-1 h-3 w-3 shrink-0 text-base-600 transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Drawer>
  );
}
