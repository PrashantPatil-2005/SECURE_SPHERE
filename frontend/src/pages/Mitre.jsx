import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import {
  Crosshair, Shield, ShieldCheck, ShieldAlert, Layers,
  ExternalLink, Loader2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/input';
import { StatCard } from '@/components/ui/stat-card';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

// Distinct colors for each MITRE tactic — pulled from Tailwind palette
// so the dark theme reads well without being garish.
const TACTIC_COLORS = {
  'Reconnaissance':       '#60a5fa', // blue-400
  'Initial Access':       '#f87171', // red-400
  'Execution':            '#fb923c', // orange-400
  'Persistence':          '#facc15', // yellow-400
  'Privilege Escalation': '#f472b6', // pink-400
  'Defense Evasion':      '#a78bfa', // violet-400
  'Credential Access':    '#fbbf24', // amber-400
  'Discovery':            '#34d399', // emerald-400
  'Lateral Movement':     '#22d3ee', // cyan-400
  'Collection':           '#c084fc', // purple-400
  'Command and Control':  '#38bdf8', // sky-400
  'Exfiltration':         '#fb7185', // rose-400
  'Impact':               '#ef4444', // red-500
  'Unknown':              '#737373', // base-500
};

const COVERAGE_BADGE = {
  full: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  partial: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  theoretical: 'bg-base-800/50 text-base-400 border-base-700',
};

const SCENARIO_COLORS = {
  A: 'bg-red-500/10 text-red-400 border-red-500/25',
  B: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
  C: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/25',
};

function tacticColor(tactic) {
  return TACTIC_COLORS[tactic] || TACTIC_COLORS.Unknown;
}

// ---------------------------------------------------------------------------

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-lg border border-base-800 bg-base-900/95 backdrop-blur-sm px-3 py-2 shadow-lg text-xs">
      <div className="font-semibold text-base-100">{row.tactic}</div>
      <div className="mt-1 font-mono text-base-400">
        {row.hit_count} hit{row.hit_count === 1 ? '' : 's'} · {row.technique_count} technique{row.technique_count === 1 ? '' : 's'}
      </div>
    </div>
  );
}

function TacticsBarChart({ techniques }) {
  const data = useMemo(() => {
    const agg = {};
    for (const t of techniques) {
      const key = t.tactic || 'Unknown';
      if (!agg[key]) agg[key] = { tactic: key, hit_count: 0, technique_count: 0 };
      agg[key].hit_count += t.hit_count || 0;
      agg[key].technique_count += 1;
    }
    return Object.values(agg).sort((a, b) => b.hit_count - a.hit_count);
  }, [techniques]);

  if (!data.length) {
    return <div className="py-10 text-center text-xs text-base-500">No tactic data yet.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
        <XAxis
          type="number"
          allowDecimals={false}
          tick={{ fontSize: 10, fill: 'var(--base-500)' }}
          stroke="transparent"
        />
        <YAxis
          type="category"
          dataKey="tactic"
          tick={{ fontSize: 11, fill: 'var(--base-400)' }}
          stroke="transparent"
          width={150}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="hit_count" radius={[0, 4, 4, 0]} barSize={18}>
          {data.map((d) => (
            <Cell key={d.tactic} fill={tacticColor(d.tactic)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------

function CoverageBadge({ coverage }) {
  const tone = COVERAGE_BADGE[coverage] || COVERAGE_BADGE.theoretical;
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border',
      tone,
    )}>
      {coverage || 'theoretical'}
    </span>
  );
}

function TacticPill({ tactic }) {
  const color = tacticColor(tactic);
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border"
      style={{ color, borderColor: `${color}50`, backgroundColor: `${color}15` }}
    >
      {tactic || 'Unknown'}
    </span>
  );
}

function ScenarioBadge({ scenario }) {
  const tone = SCENARIO_COLORS[scenario] || 'bg-base-800/40 text-base-400 border-base-700';
  return (
    <span className={cn(
      'inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold font-mono border',
      tone,
    )}>
      {scenario}
    </span>
  );
}

function TechniquesTable({ techniques }) {
  if (!techniques.length) {
    return (
      <CardContent className="py-12 text-center">
        <p className="text-xs text-base-500">No techniques match the current filters.</p>
      </CardContent>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[9px] uppercase tracking-wider text-base-500 border-b border-base-800 bg-base-950/40">
            <th className="text-left font-semibold py-2 px-3">Technique ID</th>
            <th className="text-left font-semibold py-2 px-3">Name</th>
            <th className="text-left font-semibold py-2 px-3">Tactic</th>
            <th className="text-left font-semibold py-2 px-3">Coverage</th>
            <th className="text-right font-semibold py-2 px-3">Hits</th>
            <th className="text-left font-semibold py-2 px-3">Detected By</th>
            <th className="text-left font-semibold py-2 px-3">Scenarios</th>
          </tr>
        </thead>
        <tbody>
          {techniques.map((t) => (
            <tr key={t.technique_id} className="border-b border-base-800/80 hover:bg-base-950/40 transition-colors">
              <td className="py-2.5 px-3 font-mono">
                <a
                  href={`https://attack.mitre.org/techniques/${t.technique_id.replace('.', '/')}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-accent hover:underline"
                  title="Open on attack.mitre.org"
                >
                  {t.technique_id}
                  <ExternalLink className="h-3 w-3 opacity-70" />
                </a>
              </td>
              <td className="py-2.5 px-3 text-base-100">
                <div className="font-medium">{t.technique_name}</div>
                {t.container_context && (
                  <div className="mt-0.5 text-[10px] text-base-500 leading-snug max-w-md">
                    {t.container_context}
                  </div>
                )}
              </td>
              <td className="py-2.5 px-3"><TacticPill tactic={t.tactic} /></td>
              <td className="py-2.5 px-3"><CoverageBadge coverage={t.coverage} /></td>
              <td className="py-2.5 px-3 text-right font-mono font-semibold text-base-100">
                {t.hit_count > 0 ? t.hit_count : <span className="text-base-500">0</span>}
              </td>
              <td className="py-2.5 px-3 text-[11px] text-base-400 font-mono">
                {(t.detected_by || []).length > 0
                  ? t.detected_by.join(', ')
                  : <span className="text-base-600 italic">—</span>}
              </td>
              <td className="py-2.5 px-3">
                <div className="flex items-center gap-1">
                  {(t.scenarios || []).length > 0
                    ? t.scenarios.map((s) => <ScenarioBadge key={s} scenario={s} />)
                    : <span className="text-base-600 text-[10px] italic">—</span>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------

function SummaryBar({ data }) {
  const totalTechniques = data?.total_techniques ?? 0;
  const fullCov = data?.full_coverage ?? 0;
  const partialCov = data?.partial_coverage ?? 0;
  const tacticsCovered = Object.keys(data?.tactics_summary || {}).length;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard
        label="Techniques Covered"
        value={totalTechniques}
        icon={Shield}
        color="accent"
        sub="mapped in MITRE registry"
      />
      <StatCard
        label="Full Coverage"
        value={fullCov}
        icon={ShieldCheck}
        color="green"
        sub="direct monitor detection"
      />
      <StatCard
        label="Partial Coverage"
        value={partialCov}
        icon={ShieldAlert}
        color="orange"
        sub="inferred via correlation"
      />
      <StatCard
        label="Tactics Covered"
        value={tacticsCovered}
        icon={Layers}
        color="cyan"
        sub="distinct kill-chain stages"
      />
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-[10px] border border-base-800 bg-base-900 p-5">
            <div className="mb-3 h-5 w-28 rounded bg-base-800/60 animate-pulse" />
            <div className="h-8 w-16 rounded bg-base-800/60 animate-pulse" />
          </div>
        ))}
      </div>
      <Card>
        <CardContent className="flex items-center justify-center gap-2 py-16 text-xs text-base-500">
          <Loader2 className="h-4 w-4 animate-spin text-accent" />
          Loading MITRE coverage…
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Mitre() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tacticFilter, setTacticFilter] = useState('all');
  const [coverageFilter, setCoverageFilter] = useState('all');

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        const res = await api.getMitreMapping();
        if (cancelled) return;
        setData(res || null);
        setError('');
      } catch (e) {
        if (!cancelled) setError('Failed to fetch MITRE mapping.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  const techniques = useMemo(() => data?.techniques || [], [data]);
  const tactics = useMemo(() => {
    const set = new Set(techniques.map((t) => t.tactic).filter(Boolean));
    return Array.from(set).sort();
  }, [techniques]);

  const filtered = useMemo(() => {
    return techniques.filter((t) => {
      if (tacticFilter !== 'all' && t.tactic !== tacticFilter) return false;
      if (coverageFilter !== 'all' && t.coverage !== coverageFilter) return false;
      return true;
    });
  }, [techniques, tacticFilter, coverageFilter]);

  if (loading && !data) return <LoadingSkeleton />;

  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-base-100">MITRE ATT&amp;CK for Containers</h2>
          <p className="mt-1 max-w-2xl text-sm text-base-500">
            Live coverage map: every technique SecuriSphere detects, the monitor or rule behind
            it, and how often it has fired in the current incident stream.
          </p>
        </div>
        <a
          href="https://attack.mitre.org/matrices/enterprise/containers/"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:underline"
        >
          Reference matrix
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      {error && !data && (
        <Card>
          <CardContent className="py-6 text-center text-xs text-red-400">{error}</CardContent>
        </Card>
      )}

      {/* Summary */}
      <SummaryBar data={data} />

      {/* Tactics bar chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Crosshair className="h-4 w-4 text-accent" />
            <CardTitle className="text-sm">Hits by Tactic</CardTitle>
            {data?.total_incidents != null && (
              <span className="ml-auto font-mono text-[10px] text-base-500">
                {data.total_incidents} incident{data.total_incidents === 1 ? '' : 's'} correlated
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <TacticsBarChart techniques={techniques} />
        </CardContent>
      </Card>

      {/* Techniques table + filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3 w-full flex-wrap">
            <CardTitle className="text-sm">Techniques</CardTitle>
            <span className="font-mono text-[10px] text-base-500">
              {filtered.length} / {techniques.length}
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Select value={tacticFilter} onChange={(e) => setTacticFilter(e.target.value)}>
                <option value="all">All Tactics</option>
                {tactics.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </Select>
              <Select value={coverageFilter} onChange={(e) => setCoverageFilter(e.target.value)}>
                <option value="all">All Coverage</option>
                <option value="full">Full</option>
                <option value="partial">Partial</option>
                <option value="theoretical">Theoretical</option>
              </Select>
            </div>
          </div>
        </CardHeader>
        <TechniquesTable techniques={filtered} />
      </Card>
    </motion.div>
  );
}
