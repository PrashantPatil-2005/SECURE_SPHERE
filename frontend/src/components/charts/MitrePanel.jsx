import { useEffect, useState, useMemo } from 'react';
import { Shield, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

/** Grayscale tiers; red only for high-impact web exploit (T1190). */
function tacticTone(techniqueId) {
  if (techniqueId === 'T1190') {
    return 'text-red-400 border-red-400/30 bg-red-400/[0.08]';
  }
  const n = String(techniqueId || '')
    .split('')
    .reduce((a, c) => a + c.charCodeAt(0), 0) % 4;
  const tones = [
    'text-base-300 border-base-700 bg-base-800/40',
    'text-base-300 border-base-800 bg-base-900/50',
    'text-base-400 border-base-800 bg-base-950/40',
    'text-base-200 border-base-600 bg-base-800/30',
  ];
  return tones[n];
}

const DEFAULT_TONE = 'text-base-300 border-base-800 bg-base-900/50';

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
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const techniques = useMemo(() => data?.techniques || [], [data]);
  const maxHits = useMemo(
    () => techniques.reduce((m, t) => Math.max(m, (t.hit_count || 0) + (t.engine_hit_count || 0)), 0),
    [techniques]
  );
  const totalUnique = data?.total_techniques ?? data?.total_unique ?? techniques.length;

  return (
    <Card className="overflow-hidden border-base-800 bg-base-900 transition-colors duration-200">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-accent" />
          <CardTitle className="text-base-100">MITRE ATT&CK Matrix</CardTitle>
          {data && (
            <span className="ml-auto font-mono text-[10px] text-base-500">
              {totalUnique} techniques · {data.total_incidents ?? 0} incidents
              {data.coverage_percent != null && <> · {data.coverage_percent}% coverage</>}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-base-500">
            <Loader2 className="h-4 w-4 animate-spin text-accent" /> Loading MITRE mapping…
          </div>
        ) : error ? (
          <div className="py-6 text-center text-xs text-base-400">{error}</div>
        ) : techniques.length === 0 ? (
          <div className="py-6 text-center text-xs text-base-500">Techniques will be mapped here as incidents develop.</div>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {techniques.map((t) => {
              const total = (t.hit_count || 0) + (t.engine_hit_count || 0);
              const pct = maxHits > 0 ? Math.min(100, (total / maxHits) * 100) : 0;
              const tone = tacticTone(t.technique_id) || DEFAULT_TONE;
              const techName = t.technique_name || t.name || '';
              const tooltip = `${t.technique_id} — ${techName}${t.description ? `\n\n${t.description}` : ''}${total ? `\n\nHits: ${total}` : ''}`;
              return (
                <div
                  key={t.technique_id}
                  className={cn(
                    'group relative cursor-help rounded border px-2 py-1.5 transition-colors duration-200 hover:brightness-110',
                    tone
                  )}
                  title={tooltip}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-semibold">{t.technique_id}</span>
                    <span className="font-mono text-[10px] opacity-70">{total}</span>
                  </div>
                  <div className="mt-0.5 truncate text-[10px] opacity-90">{techName}</div>
                  <div className="mt-1 h-0.5 w-full overflow-hidden rounded-full bg-base-950/50">
                    <div className="h-full rounded-full bg-current opacity-60" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="pointer-events-none absolute left-1/2 top-full z-20 mt-1 hidden w-56 -translate-x-1/2 group-hover:block">
                    <div className="rounded border border-base-800 bg-base-950 p-2 text-[10px] leading-snug text-base-200 shadow-lg">
                      <div className="font-mono font-semibold text-base-100">
                        {t.technique_id} · {techName}
                      </div>
                      {t.description && <div className="mt-1 text-base-400">{t.description}</div>}
                      {total > 0 && (
                        <div className="mt-1 font-mono text-accent">
                          {total} hit{total === 1 ? '' : 's'}
                        </div>
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
