import { useEffect, useState } from 'react';
import { Check, X, Circle, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { api } from '@/lib/api';

const GLYPH = {
  pass: { Icon: Check, cls: 'text-base-400' },
  fail: { Icon: X, cls: 'text-base-600' },
  static: { Icon: Circle, cls: 'text-base-600' },
};

function StatusPill({ status }) {
  const map = {
    ready: { label: 'Ready', cls: 'border-base-700 bg-base-800/50 text-base-200' },
    in_progress: { label: 'In progress', cls: 'border-base-700 bg-base-900/60 text-base-300' },
  };
  const s = map[status] || { label: status, cls: 'border-base-800 bg-base-950/40 text-base-400' };
  return (
    <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider transition-colors duration-200 ${s.cls}`}>
      {s.label}
    </span>
  );
}

export default function TopologyChecklist() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await api.getTopologyChecks();
        if (alive) {
          setData(d);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(e.message || 'fetch failed');
      }
    };
    load();
    const t = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  if (error && !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Topology checkpoint</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-2 text-xs text-base-500">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>Status unavailable: {error}</span>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Topology checkpoint</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-base-500">Loading…</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex items-start justify-between gap-2">
        <div className="flex flex-col">
          <CardTitle>{data.title}</CardTitle>
          <span className="mt-0.5 text-[11px] text-base-500">{data.subtitle}</span>
        </div>
        <StatusPill status={data.status} />
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {data.checks.map((c) => {
          const { Icon, cls } = GLYPH[c.state] || GLYPH.static;
          return (
            <div key={c.id} className="flex items-center gap-2">
              <Icon className={`h-3.5 w-3.5 shrink-0 ${cls}`} />
              <span className="flex-1 text-xs leading-snug text-base-200">{c.label}</span>
              <span className="rounded border border-base-800 bg-base-950/40 px-1.5 py-0.5 font-mono text-[10px] text-base-500">
                {c.evidence}
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
