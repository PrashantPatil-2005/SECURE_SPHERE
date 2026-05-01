import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ScrollText, Loader2, RefreshCw, Filter, X, ChevronRight, ChevronDown, Shield, AlertTriangle, AlertOctagon, Info,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Input, Select } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { StatCard } from '@/components/ui/stat-card';
import { api } from '@/lib/api';
import { cn, formatTimestampFull, relativeTime } from '@/lib/utils';

const REFRESH_MS = 10_000;

const SEV_TONE = {
  critical: 'border-red-500/40 bg-red-500/10 text-red-300',
  warning:  'border-amber-500/35 bg-amber-500/10 text-amber-200',
  info:     'border-sky-500/30 bg-sky-500/10 text-sky-200',
};

const SEV_DOT = {
  critical: 'bg-red-400',
  warning:  'bg-amber-400',
  info:     'bg-sky-400',
};

const SEV_ICON = {
  critical: AlertOctagon,
  warning:  AlertTriangle,
  info:     Info,
};

const ACTOR_TONE = {
  user:   'bg-violet-500/10 text-violet-300 border-violet-500/30',
  engine: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  system: 'bg-base-800/60 text-base-300 border-base-700',
};

function SeverityChip({ sev }) {
  const key = (sev || 'info').toLowerCase();
  const Icon = SEV_ICON[key] || Info;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider',
        SEV_TONE[key] || SEV_TONE.info,
      )}
    >
      <Icon className="h-3 w-3" />
      {key}
    </span>
  );
}

function ActorChip({ actor, actorType }) {
  const tone = ACTOR_TONE[actorType] || ACTOR_TONE.system;
  return (
    <span className={cn('inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[10px]', tone)}>
      <span className="opacity-60">{actorType || 'system'}</span>
      <span className="opacity-30">·</span>
      <span>{actor}</span>
    </span>
  );
}

function DetailJson({ detail }) {
  const text = useMemo(() => {
    try {
      return JSON.stringify(detail || {}, null, 2);
    } catch {
      return String(detail);
    }
  }, [detail]);
  return (
    <pre className="mt-2 max-h-80 overflow-auto rounded-md border border-base-800 bg-base-950/70 p-3 font-mono text-[11px] leading-relaxed text-base-300">
      {text}
    </pre>
  );
}

function AuditRow({ row, expanded, onToggle }) {
  const Icon = expanded ? ChevronDown : ChevronRight;
  return (
    <>
      <tr
        onClick={onToggle}
        className={cn(
          'cursor-pointer border-t border-base-900 transition-colors hover:bg-base-950/60',
          expanded && 'bg-base-950/70',
        )}
      >
        <td className="w-6 py-2 pl-3 align-top">
          <Icon className="h-3.5 w-3.5 text-base-500" />
        </td>
        <td className="py-2 align-top">
          <div className="flex items-center gap-2">
            <span className={cn('h-1.5 w-1.5 rounded-full', SEV_DOT[(row.severity || 'info').toLowerCase()] || SEV_DOT.info)} />
            <span className="font-mono text-xs text-base-200">{row.action}</span>
          </div>
          {row.target_type && (
            <div className="mt-1 font-mono text-[10px] text-base-500">
              {row.target_type}
              {row.target_id && (
                <>
                  <span className="opacity-40">·</span> {row.target_id}
                </>
              )}
            </div>
          )}
        </td>
        <td className="py-2 align-top">
          <ActorChip actor={row.actor} actorType={row.actor_type} />
        </td>
        <td className="py-2 align-top">
          <SeverityChip sev={row.severity} />
        </td>
        <td className="py-2 align-top font-mono text-[11px] text-base-400">
          {row.source_ip || <span className="text-base-600">—</span>}
        </td>
        <td className="py-2 pr-3 text-right align-top">
          <div className="font-mono text-[11px] text-base-300" title={formatTimestampFull(row.timestamp)}>
            {relativeTime(row.timestamp)}
          </div>
          <div className="font-mono text-[10px] text-base-500">{formatTimestampFull(row.timestamp)}</div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-base-900 bg-base-950/40">
          <td />
          <td colSpan={5} className="px-3 pb-3 pt-1">
            <DetailJson detail={row.detail} />
          </td>
        </tr>
      )}
    </>
  );
}

const anim = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

export default function Audit() {
  const [filters, setFilters] = useState({ actor: '', action: '', severity: '', from: '', to: '', limit: 100 });
  const [data, setData] = useState({ total: 0, logs: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(() => new Set());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const lastFetch = useRef(0);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAuditLogs(filters);
      setData(res || { total: 0, logs: [] });
      lastFetch.current = Date.now();
    } catch (e) {
      setError(e?.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const id = setInterval(fetchLogs, REFRESH_MS);
    return () => clearInterval(id);
  }, [autoRefresh, fetchLogs]);

  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const counts = useMemo(() => {
    const c = { critical: 0, warning: 0, info: 0 };
    for (const r of data.logs) {
      const k = (r.severity || 'info').toLowerCase();
      if (c[k] !== undefined) c[k] += 1;
    }
    return c;
  }, [data.logs]);

  const updateFilter = (k, v) => setFilters((f) => ({ ...f, [k]: v }));

  const clearFilters = () => setFilters({ actor: '', action: '', severity: '', from: '', to: '', limit: 100 });

  return (
    <motion.div {...anim} className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-semibold text-base-100">
            <ScrollText className="h-5 w-5 text-accent" />
            Audit Log
          </h1>
          <p className="mt-1 text-xs text-base-400">
            Append-only system audit trail. Engine rule firings, kill-chain creations, login activity, incident triage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-xs text-base-400">
            <input
              type="checkbox"
              className="accent-accent"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh 10s
          </label>
          <Button variant="ghost" size="sm" onClick={fetchLogs} disabled={loading}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            <span className="ml-1">Refresh</span>
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Total"    value={data.total}      icon={ScrollText}    color="muted" />
        <StatCard label="Critical" value={counts.critical} icon={AlertOctagon}  color="red" />
        <StatCard label="Warning"  value={counts.warning}  icon={AlertTriangle} color="amber" />
        <StatCard label="Info"     value={counts.info}     icon={Info}          color="cyan" />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Filter className="h-3.5 w-3.5 text-base-400" /> Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-6">
            <Input
              placeholder="actor"
              value={filters.actor}
              onChange={(e) => updateFilter('actor', e.target.value)}
            />
            <Input
              placeholder="action prefix (e.g. kill_chain)"
              value={filters.action}
              onChange={(e) => updateFilter('action', e.target.value)}
            />
            <Select
              value={filters.severity}
              onChange={(e) => updateFilter('severity', e.target.value)}
            >
              <option value="">all severities</option>
              <option value="info">info</option>
              <option value="warning">warning</option>
              <option value="critical">critical</option>
            </Select>
            <Input
              type="datetime-local"
              value={filters.from}
              onChange={(e) => updateFilter('from', e.target.value)}
            />
            <Input
              type="datetime-local"
              value={filters.to}
              onChange={(e) => updateFilter('to', e.target.value)}
            />
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min={1}
                max={500}
                value={filters.limit}
                onChange={(e) => updateFilter('limit', Number(e.target.value) || 100)}
              />
              <Button variant="ghost" size="icon" onClick={clearFilters} title="Clear filters">
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm">
            Entries
            <span className="ml-2 font-mono text-[11px] text-base-500">
              {data.logs.length} of {data.total}
            </span>
          </CardTitle>
          {error && (
            <span className="font-mono text-[11px] text-red-400">{error}</span>
          )}
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-base-950/50 text-[10px] uppercase tracking-wider text-base-500">
                <tr>
                  <th className="w-6 py-2 pl-3" />
                  <th className="py-2">Action / Target</th>
                  <th className="py-2">Actor</th>
                  <th className="py-2">Severity</th>
                  <th className="py-2">Source IP</th>
                  <th className="py-2 pr-3 text-right">When</th>
                </tr>
              </thead>
              <tbody>
                {data.logs.length === 0 && !loading && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-base-500">
                      <Shield className="mx-auto mb-2 h-6 w-6 opacity-40" />
                      No audit entries match current filters.
                    </td>
                  </tr>
                )}
                {data.logs.map((row) => (
                  <AuditRow
                    key={row.id}
                    row={row}
                    expanded={expanded.has(row.id)}
                    onToggle={() => toggle(row.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
