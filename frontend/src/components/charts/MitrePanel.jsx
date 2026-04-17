import { useEffect, useState, useMemo } from 'react';
import { Shield, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const TACTIC_COLORS = {
  T1046: 'text-sky-400 border-sky-400/30 bg-sky-400/[0.08]',
  T1595: 'text-sky-400 border-sky-400/30 bg-sky-400/[0.08]',
  T1526: 'text-sky-400 border-sky-400/30 bg-sky-400/[0.08]',
  T1083: 'text-sky-400 border-sky-400/30 bg-sky-400/[0.08]',
  T1190: 'text-red-400 border-red-400/30 bg-red-400/[0.08]',
  T1110: 'text-amber-400 border-amber-400/30 bg-amber-400/[0.08]',
  'T1110.004': 'text-amber-400 border-amber-400/30 bg-amber-400/[0.08]',
  T1078: 'text-amber-400 border-amber-400/30 bg-amber-400/[0.08]',
  T1003: 'text-amber-400 border-amber-400/30 bg-amber-400/[0.08]',
  T1068: 'text-orange-400 border-orange-400/30 bg-orange-400/[0.08]',
  T1548: 'text-orange-400 border-orange-400/30 bg-orange-400/[0.08]',
  T1021: 'text-purple-400 border-purple-400/30 bg-purple-400/[0.08]',
  T1570: 'text-purple-400 border-purple-400/30 bg-purple-400/[0.08]',
  T1071: 'text-pink-400 border-pink-400/30 bg-pink-400/[0.08]',
  T1041: 'text-rose-400 border-rose-400/30 bg-rose-400/[0.08]',
  T1048: 'text-rose-400 border-rose-400/30 bg-rose-400/[0.08]',
  T1530: 'text-emerald-400 border-emerald-400/30 bg-emerald-400/[0.08]',
};

const DEFAULT_TONE = 'text-base-300 border-white/10 bg-white/[0.04]';

export default function MitrePanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        const res = await api.getMitreMapping();
        if (cancelled) return;
        setData(res || null);
        setError('');
      } catch (e) {
        if (!cancelled) setError('Network error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    const id = setInterval(fetchData, 15000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const techniques = useMemo(() => data?.techniques || [], [data]);
  const maxHits = useMemo(
    () => techniques.reduce((m, t) => Math.max(m, (t.hit_count || 0) + (t.engine_hit_count || 0)), 0),
    [techniques]
  );

  return (
    <Card className="overflow-hidden bg-base-900 border-white/[0.05]">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" />
          <CardTitle className="text-base-100">MITRE ATT&CK Matrix</CardTitle>
          {data && (
            <span className="ml-auto text-[10px] font-mono text-base-500">
              {data.total_unique ?? 0} techniques · {data.total_incidents ?? 0} incidents
              {data.coverage_percent != null && (
                <> · {data.coverage_percent}% coverage</>
              )}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="py-8 flex items-center justify-center text-xs text-base-500 gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading MITRE mapping…
          </div>
        ) : error ? (
          <div className="py-6 text-center text-xs text-red-400">{error}</div>
        ) : techniques.length === 0 ? (
          <div className="py-6 text-center text-xs text-base-500">
            Techniques will be mapped here as incidents develop.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {techniques.map((t) => {
              const total = (t.hit_count || 0) + (t.engine_hit_count || 0);
              const pct = maxHits > 0 ? Math.min(100, (total / maxHits) * 100) : 0;
              const tone = TACTIC_COLORS[t.technique_id] || DEFAULT_TONE;
              const tooltip = `${t.technique_id} — ${t.name}${t.description ? `\n\n${t.description}` : ''}${total ? `\n\nHits: ${total}` : ''}`;
              return (
                <div
                  key={t.technique_id}
                  className={cn(
                    'group relative rounded border px-2 py-1.5 cursor-help transition-colors hover:brightness-125',
                    tone
                  )}
                  title={tooltip}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-semibold">{t.technique_id}</span>
                    <span className="text-[10px] font-mono opacity-70">{total}</span>
                  </div>
                  <div className="text-[10px] mt-0.5 truncate opacity-90">{t.name}</div>
                  <div className="mt-1 h-0.5 w-full bg-black/30 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-current opacity-60"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="pointer-events-none absolute z-20 left-1/2 -translate-x-1/2 top-full mt-1 w-56 hidden group-hover:block">
                    <div className="rounded border border-white/10 bg-base-950 shadow-lg p-2 text-[10px] leading-snug text-base-200">
                      <div className="font-mono font-semibold text-base-100">
                        {t.technique_id} · {t.name}
                      </div>
                      {t.description && (
                        <div className="mt-1 text-base-400">{t.description}</div>
                      )}
                      {total > 0 && (
                        <div className="mt-1 font-mono text-accent">{total} hit{total === 1 ? '' : 's'}</div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
