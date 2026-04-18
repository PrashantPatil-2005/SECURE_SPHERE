import { useEffect, useState, useMemo } from 'react';
import { Clock, Database, Zap, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const fmtSec = (v) => {
  if (v == null) return '\u2014';
  if (v < 1) return `${Math.round(v * 1000)}ms`;
  if (v < 60) return `${v.toFixed(2)}s`;
  const m = Math.floor(v / 60);
  const s = Math.round(v - m * 60);
  return `${m}m ${s}s`;
};

const prettyType = (t) =>
  (t || 'unknown')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

const mttdTone = (v) => {
  if (v == null) return 'text-base-500';
  if (v < 5) return 'text-severity-low';
  if (v < 30) return 'text-severity-medium';
  if (v < 120) return 'text-severity-high';
  return 'text-severity-critical';
};

export default function MttdPanel() {
  const [rows, setRows] = useState([]);
  const [source, setSource] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        const res = await api.getMttdReport();
        if (cancelled) return;
        if (res?.status === 'success') {
          setRows(Array.isArray(res.data) ? res.data : []);
          setSource(res.source || null);
          setError('');
        } else {
          setError(res?.message || 'Failed to load MTTD report');
        }
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

  const maxAvg = useMemo(
    () => rows.reduce((m, r) => Math.max(m, r.avg_mttd_seconds || 0), 0),
    [rows]
  );

  const totals = useMemo(() => {
    const count = rows.reduce((s, r) => s + (r.incident_count || 0), 0);
    const weighted = rows.reduce((s, r) => s + (r.avg_mttd_seconds || 0) * (r.incident_count || 0), 0);
    const avg = count > 0 ? weighted / count : null;
    return { count, avg };
  }, [rows]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-accent" />
          <CardTitle>Mean Time To Detect</CardTitle>
          {source && (
            <span
              className={cn(
                'text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase tracking-wider',
                source === 'postgresql'
                  ? 'text-severity-low border-severity-low/25 bg-severity-low/[0.08]'
                  : 'text-severity-medium border-severity-medium/25 bg-severity-medium/[0.08]'
              )}
              title={source === 'postgresql' ? 'From kill_chains table' : 'Approximated from Redis'}
            >
              {source === 'postgresql' ? (
                <><Database className="w-2.5 h-2.5 inline mr-1" />pg</>
              ) : (
                <><Zap className="w-2.5 h-2.5 inline mr-1" />redis</>
              )}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-base-500">
          <span>{totals.count} incidents</span>
          {totals.avg != null && (
            <span>overall avg <span className={mttdTone(totals.avg)}>{fmtSec(totals.avg)}</span></span>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-3">
        {loading ? (
          <div className="py-8 flex items-center justify-center text-xs text-base-500 gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading MTTD report…
          </div>
        ) : error ? (
          <div className="py-6 text-center text-xs text-base-400">{error}</div>
        ) : rows.length === 0 ? (
          <div className="py-8 text-center text-xs text-base-500">No MTTD data yet — run an attack scenario.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-base-500 border-b border-base-800">
                  <th className="text-left font-semibold py-2 pl-1">Incident type</th>
                  <th className="text-right font-semibold py-2 px-2">Count</th>
                  <th className="text-right font-semibold py-2 px-2">Avg MTTD</th>
                  <th className="text-left font-semibold py-2 px-2 min-w-[100px]">Distribution</th>
                  <th className="text-right font-semibold py-2 px-2">Min</th>
                  <th className="text-right font-semibold py-2 px-2">Max</th>
                  <th className="text-right font-semibold py-2 pr-1">Attack dur.</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const pct = maxAvg > 0 ? Math.min(100, ((r.avg_mttd_seconds || 0) / maxAvg) * 100) : 0;
                  const tone = mttdTone(r.avg_mttd_seconds);
                  return (
                    <tr key={r.incident_type || i} className="border-b border-base-800 hover:bg-base-950/35">
                      <td className="py-2 pl-1 font-medium text-base-200">{prettyType(r.incident_type)}</td>
                      <td className="py-2 px-2 text-right font-mono text-base-300">{r.incident_count}</td>
                      <td className={cn('py-2 px-2 text-right font-mono font-semibold', tone)}>
                        {fmtSec(r.avg_mttd_seconds)}
                      </td>
                      <td className="py-2 px-2">
                        <div className="h-1.5 w-full bg-black/30 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-accent/70"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-base-400">{fmtSec(r.min_mttd_seconds)}</td>
                      <td className="py-2 px-2 text-right font-mono text-base-400">{fmtSec(r.max_mttd_seconds)}</td>
                      <td className="py-2 pr-1 text-right font-mono text-base-400">{fmtSec(r.avg_attack_duration_seconds)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
