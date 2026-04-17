import { useEffect, useState } from 'react';
import { Check, X, Circle, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { api } from '@/lib/api';

const GLYPH = {
  pass:   { Icon: Check,  cls: 'text-emerald-400' },
  fail:   { Icon: X,      cls: 'text-rose-400' },
  static: { Icon: Circle, cls: 'text-base-600' },
};

function StatusPill({ status }) {
  const map = {
    ready:       { label: 'Ready',       cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
    in_progress: { label: 'In progress', cls: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  };
  const s = map[status] || { label: status, cls: 'bg-white/5 text-base-400 border-white/10' };
  return (
    <span className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border ${s.cls}`}>
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
        if (alive) { setData(d); setError(null); }
      } catch (e) {
        if (alive) setError(e.message || 'fetch failed');
      }
    };
    load();
    const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  if (error && !data) {
    return (
      <Card>
        <CardHeader><CardTitle>Topology checkpoint</CardTitle></CardHeader>
        <CardContent className="flex items-center gap-2 text-amber-400 text-xs">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Status unavailable: {error}</span>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader><CardTitle>Topology checkpoint</CardTitle></CardHeader>
        <CardContent className="text-xs text-base-500">Loading…</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex items-start justify-between gap-2">
        <div className="flex flex-col">
          <CardTitle>{data.title}</CardTitle>
          <span className="text-[11px] text-base-500 mt-0.5">{data.subtitle}</span>
        </div>
        <StatusPill status={data.status} />
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {data.checks.map((c) => {
          const { Icon, cls } = GLYPH[c.state] || GLYPH.static;
          return (
            <div key={c.id} className="flex items-center gap-2">
              <Icon className={`w-3.5 h-3.5 shrink-0 ${cls}`} />
              <span className="text-xs text-base-200 flex-1 leading-snug">{c.label}</span>
              <span className="text-[10px] font-mono text-base-500 border border-white/10 rounded px-1.5 py-0.5 bg-white/[0.02]">
                {c.evidence}
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
