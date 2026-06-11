import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import {
  CheckCircle2, XCircle, Activity, Gauge, ShieldCheck, AlertTriangle, Zap,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { StatCard } from '@/components/ui/stat-card';
import SparkLine from '@/components/charts/SparkLine';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const ARROW = '\u2192';
const SIGMA = '\u03c3';
const GE = '\u2265';

const FALLBACK = {
  generated_at: '2026-04-18',
  overall: {
    mttd_raw_logs_seconds: 252.8,
    mttd_dashboard_seconds: 6.75,
    reduction_percent: 97.33,
    target_reduction_percent: 70.0,
    target_met: true,
    backend_correlation_latency_seconds: 0.08,
  },
  scenarios: [
    {
      name: 'Scenario A',
      description: `Brute Force ${ARROW} Credential Compromise ${ARROW} Data Exfiltration`,
      mttd_raw: 247.0, mttd_dashboard: 6.0, reduction_percent: 97.57,
      raw_trials: [239, 255, 247], dashboard_trials: [6.01, 6.0, 6.0],
      raw_stddev: 6.53, dashboard_stddev: 0.005,
    },
    {
      name: 'Scenario B',
      description: `Recon ${ARROW} SQL Injection ${ARROW} Privilege Escalation`,
      mttd_raw: 199.3, mttd_dashboard: 8.14, reduction_percent: 95.91,
      raw_trials: [194, 206, 198], dashboard_trials: [8.15, 8.14, 8.14],
      raw_stddev: 5.03, dashboard_stddev: 0.005,
    },
    {
      name: 'Scenario C',
      description: 'Multi-Hop Lateral Movement (4 hops)',
      mttd_raw: 312.0, mttd_dashboard: 6.11, reduction_percent: 98.04,
      raw_trials: [305, 319, 312], dashboard_trials: [6.12, 6.13, 6.08],
      raw_stddev: 5.72, dashboard_stddev: 0.022,
    },
  ],
  system_metrics: {
    trials_completed: 18, trials_total: 18,
    false_positives_benign: 0, detection_rate_percent: 100.0,
  },
  methodology_note: 'Raw-log baselines use simulated analyst timing from baseline_mttd.py modeling realistic scroll/search cognitive load. Dashboard timings measured from kill_chains.mttd_seconds + UI overhead (3s poll + 1s render + 2s operator read).',
};

const RAW_COLOR = '#ef4444';
const DASH_COLOR = '#10b981';

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const raw = payload.find((p) => p.dataKey === 'raw')?.value;
  const dash = payload.find((p) => p.dataKey === 'dashboard')?.value;
  const pct = raw && dash ? (((raw - dash) / raw) * 100).toFixed(2) : null;
  return (
    <div className="rounded border border-base-700 bg-base-950 px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 font-semibold text-base-100">{label}</div>
      <div className="flex items-center gap-2 text-red-400">
        <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
        Raw Logs: <span className="font-mono tabular-nums">{raw}s</span>
      </div>
      <div className="flex items-center gap-2 text-emerald-400">
        <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
        Dashboard: <span className="font-mono tabular-nums">{dash}s</span>
      </div>
      {pct && (
        <div className="mt-1 border-t border-base-800 pt-1 font-mono text-[11px] text-base-400">
          Reduction: <span className="text-emerald-400">{pct}%</span>
        </div>
      )}
    </div>
  );
}

function ScenarioCard({ scenario }) {
  const targetMet = scenario.reduction_percent >= 70;
  const rawSpark = (scenario.raw_trials || []).map((v) => ({ value: v }));
  const dashSpark = (scenario.dashboard_trials || []).map((v) => ({ value: v }));

  return (
    <Card>
      <CardContent className="p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-base-100">{scenario.name}</h3>
            <p className="mt-0.5 text-xs text-base-400">{scenario.description}</p>
          </div>
          {targetMet ? (
            <span className="inline-flex shrink-0 items-center gap-1 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
              <CheckCircle2 className="h-3 w-3" /> Target Met
            </span>
          ) : (
            <span className="inline-flex shrink-0 items-center gap-1 rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              <XCircle className="h-3 w-3" /> Target Not Met
            </span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3 border-t border-base-800 pt-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-base-500">MTTD Raw</div>
            <div className="font-mono text-lg tabular-nums text-red-400">{scenario.mttd_raw}s</div>
            <div className="mt-1"><SparkLine data={rawSpark} color={RAW_COLOR} height={24} /></div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-base-500">Dashboard</div>
            <div className="font-mono text-lg tabular-nums text-emerald-400">{scenario.mttd_dashboard}s</div>
            <div className="mt-1"><SparkLine data={dashSpark} color={DASH_COLOR} height={24} /></div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-base-500">Reduction</div>
            <div className="font-mono text-lg tabular-nums text-accent">
              {scenario.reduction_percent.toFixed(2)}%
            </div>
            <div className="mt-1 font-mono text-[10px] text-base-500">
              {SIGMA} raw {Number(scenario.raw_stddev).toFixed(2)} · {SIGMA} dash {Number(scenario.dashboard_stddev).toFixed(3)}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Evaluation() {
  const [data, setData] = useState(FALLBACK);
  const [usedFallback, setUsedFallback] = useState(true);

  useEffect(() => {
    let cancel = false;
    api.getEvaluationResults()
      .then((res) => {
        if (cancel) return;
        if (res && typeof res === 'object' && res.overall && Array.isArray(res.scenarios)) {
          setData(res);
          setUsedFallback(false);
        }
      })
      .catch(() => { /* keep fallback */ });
    return () => { cancel = true; };
  }, []);

  const overall = data.overall || {};
  const scenarios = data.scenarios || [];
  const sysm = data.system_metrics || {};
  const targetMet = overall.target_met ?? (overall.reduction_percent >= (overall.target_reduction_percent || 70));

  const chartData = scenarios.map((s) => ({
    name: s.name,
    raw: s.mttd_raw,
    dashboard: s.mttd_dashboard,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex max-w-6xl flex-col gap-6"
    >
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-base-100">Evaluation Results</h1>
            <p className="mt-1 text-sm text-base-400">
              MTTD reduction across three named kill-chain scenarios. Reviewer-facing summary.
            </p>
          </div>
          <Link to="/dashboard" className="text-xs text-accent hover:underline">Back to dashboard</Link>
        </header>

        {/* Section 1 — Hero */}
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10">
            <div className="text-[11px] uppercase tracking-[0.2em] text-base-500">
              Mean Time to Detect — Reduction
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-6xl font-bold tabular-nums text-accent">
                {Number(overall.reduction_percent || 0).toFixed(2)}%
              </span>
              {targetMet && <CheckCircle2 className="h-10 w-10 text-emerald-400" />}
            </div>
            <div
              className={cn(
                'flex items-center gap-2 rounded-full border px-3 py-1 text-xs',
                targetMet
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                  : 'border-red-500/40 bg-red-500/10 text-red-400'
              )}
            >
              <span>Target: {GE}{overall.target_reduction_percent ?? 70}%</span>
              {targetMet ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
            </div>
            <div className="mt-2 flex flex-wrap items-center justify-center gap-x-6 gap-y-1 text-xs text-base-400">
              <span>
                Raw logs:{' '}
                <span className="font-mono tabular-nums text-red-400">
                  {overall.mttd_raw_logs_seconds}s
                </span>
              </span>
              <span>
                Dashboard:{' '}
                <span className="font-mono tabular-nums text-emerald-400">
                  {overall.mttd_dashboard_seconds}s
                </span>
              </span>
              <span>
                Backend correlation:{' '}
                <span className="font-mono tabular-nums text-base-200">
                  {overall.backend_correlation_latency_seconds}s
                </span>
              </span>
              {usedFallback && (
                <span className="inline-flex items-center gap-1 text-amber-400">
                  <AlertTriangle className="h-3 w-3" /> Showing bundled results (API unavailable)
                </span>
              )}
              {data.generated_at && (
                <span className="font-mono text-base-500">Generated {data.generated_at}</span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Section 2 — Bar chart */}
        <Card>
          <CardContent className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-base-100">MTTD: Raw Logs vs Dashboard</h2>
              <span className="font-mono text-[10px] text-base-500">seconds (lower is better)</span>
            </div>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 12, right: 16, bottom: 12, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--base-800)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: 'var(--base-400)', fontSize: 12 }} axisLine={{ stroke: 'var(--base-800)' }} />
                  <YAxis tick={{ fill: 'var(--base-400)', fontSize: 12 }} axisLine={{ stroke: 'var(--base-800)' }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Legend wrapperStyle={{ fontSize: 12, color: 'var(--base-300)' }} />
                  <Bar dataKey="raw" name="Raw Logs" fill={RAW_COLOR} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="dashboard" name="SecuriSphere Dashboard" fill={DASH_COLOR} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Section 3 — Per-scenario cards */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {scenarios.map((s) => (
            <ScenarioCard key={s.name} scenario={s} />
          ))}
        </div>

        {/* Section 5 — System metrics */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard
            label="Backend Correlation"
            value={`${overall.backend_correlation_latency_seconds ?? '—'}s`}
            icon={Zap}
            color="accent"
            sub="kill_chains.mttd_seconds median"
          />
          <StatCard
            label="Trials Completed"
            value={`${sysm.trials_completed ?? 0}/${sysm.trials_total ?? 0}`}
            icon={Activity}
            color="cyan"
            sub="9 attack + 9 baseline"
          />
          <StatCard
            label="False Positives"
            value={sysm.false_positives_benign ?? 0}
            icon={ShieldCheck}
            color="green"
            sub="benign baseline"
          />
          <StatCard
            label="Detection Rate"
            value={`${Number(sysm.detection_rate_percent ?? 0).toFixed(0)}%`}
            icon={Gauge}
            color="amber"
            sub="all attack stages detected"
          />
        </div>

        {/* Section 4 — Methodology */}
        <Card>
          <CardContent className="p-5">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-base-100 [&::-webkit-details-marker]:hidden">
                <span>Methodology note</span>
                <span className="font-mono text-xs text-base-500 transition-transform group-open:rotate-180">▾</span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-base-300">
                {data.methodology_note}
              </p>
              <p className="mt-2 text-xs text-base-500">
                See <code className="rounded bg-base-950 px-1 py-0.5 font-mono text-[11px]">experiment/results.md</code> § Methodology Transparency for the full statement on Condition A vs Condition B measurement.
              </p>
            </details>
          </CardContent>
        </Card>
    </motion.div>
  );
}
