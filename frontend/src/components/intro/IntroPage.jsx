import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  Shield, Network, Target, Activity, Zap, GitBranch,
  Eye, Clock, Gauge, CheckCircle2, ArrowRight, Play,
  Layers, AlertTriangle, Boxes,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const fade = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };
const rise = (i = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3, delay: 0.05 + i * 0.05 },
});

function Stat({ value, label, sub }) {
  return (
    <div className="rounded-lg border border-base-800 bg-base-900/60 p-4">
      <div className="text-3xl font-bold tracking-tight text-base-100 tabular-nums font-mono">
        {value}
      </div>
      <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-accent">
        {label}
      </div>
      {sub && <div className="mt-1 text-[11px] text-base-500 leading-snug">{sub}</div>}
    </div>
  );
}

function Feature({ icon: Icon, title, text, delay = 0 }) {
  return (
    <motion.div
      {...rise(delay)}
      className="group rounded-lg border border-base-800 bg-base-900/40 p-4 transition-colors hover:border-accent/30 hover:bg-base-900/70"
    >
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md border border-base-800 bg-base-950 text-accent group-hover:border-accent/30">
        <Icon className="h-4 w-4" />
      </div>
      <div className="mb-1.5 text-sm font-semibold text-base-100">{title}</div>
      <p className="text-[12px] leading-relaxed text-base-400">{text}</p>
    </motion.div>
  );
}

function CompareRow({ what, legacy, us, highlight = false }) {
  return (
    <tr className={cn('border-b border-base-800', highlight && 'bg-accent/[0.03]')}>
      <td className="py-2.5 px-3 text-[12px] text-base-300">{what}</td>
      <td className="py-2.5 px-3 text-[12px] text-base-500 font-mono">{legacy}</td>
      <td className="py-2.5 px-3 text-[12px] text-emerald-300 font-mono font-semibold">{us}</td>
    </tr>
  );
}

export default function IntroPage() {
  return (
    <motion.div {...fade} className="mx-auto max-w-6xl space-y-10 text-base-200 pb-10">
      {/* ----------------------------- HERO ----------------------------- */}
      <section className="relative overflow-hidden rounded-2xl border border-base-800 bg-gradient-to-br from-base-900 via-base-950 to-base-900 p-8 md:p-12">
        <div
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            background:
              'radial-gradient(ellipse at top right, rgba(239,68,68,0.18), transparent 55%), radial-gradient(ellipse at bottom left, rgba(16,185,129,0.12), transparent 55%)',
          }}
        />
        <div className="relative flex flex-col items-start gap-5">
          <span className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-accent">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
            Container-native SIEM · live demo ready
          </span>

          <h1 className="max-w-3xl text-3xl font-bold leading-tight tracking-tight text-base-100 md:text-5xl">
            Catch lateral movement between microservices <span className="text-accent">before</span> data walks out.
          </h1>

          <p className="max-w-2xl text-sm leading-relaxed text-base-400 md:text-base">
            SecuriSphere is the first open-source SIEM that correlates attacks by{' '}
            <span className="font-semibold text-base-100">service identity</span> — not ephemeral container IPs.
            It stitches network, API and auth signals into a single live kill-chain on your service dependency graph,
            in real time.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-md border border-accent/40 bg-accent/15 px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-accent/25"
            >
              <Play className="h-4 w-4" fill="currentColor" />
              Open the console
            </Link>
            <Link
              to="/topology"
              className="inline-flex items-center gap-2 rounded-md border border-base-700 bg-base-900/60 px-4 py-2 text-sm text-base-200 transition-colors hover:bg-base-800"
            >
              <Network className="h-4 w-4" />
              See the live graph
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="mt-2 grid w-full grid-cols-2 gap-3 md:grid-cols-4">
            <Stat value="6.0s" label="MTTD · Scenario A" sub="vs 247s raw logs" />
            <Stat value="97.57%" label="MTTD reduction" sub="against baseline SIEM" />
            <Stat value="99.97%" label="Alert reduction" sub="raw events → incidents" />
            <Stat value="3-layer" label="Coverage" sub="network · API · auth" />
          </div>
        </div>
      </section>

      {/* ----------------------------- PROBLEM ----------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-red-400">
            The blind spot
          </h2>
        </div>
        <h3 className="max-w-3xl text-2xl font-bold leading-tight text-base-100 md:text-3xl">
          Legacy SIEMs correlate by IP. Containers rotate IPs every restart.
        </h3>
        <p className="max-w-3xl text-sm leading-relaxed text-base-400">
          An attacker who brute-forces <code className="rounded bg-base-900 px-1 font-mono text-[11px]">auth-service</code>,
          pivots to <code className="rounded bg-base-900 px-1 font-mono text-[11px]">api-gateway</code>, then exfiltrates
          from <code className="rounded bg-base-900 px-1 font-mono text-[11px]">payment-service</code> produces{' '}
          <span className="text-red-400 font-semibold">three unrelated alerts</span> on three rotated IPs in tools like
          Splunk, Wazuh or Elastic. The kill chain never gets assembled — and the breach reads as noise.
        </p>
      </section>

      {/* ----------------------------- WHAT WE DO ----------------------------- */}
      <section className="space-y-5">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-accent" />
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            What SecuriSphere does
          </h2>
        </div>
        <h3 className="max-w-3xl text-2xl font-bold leading-tight text-base-100 md:text-3xl">
          One engine. Three layers. Full kill chain.
        </h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <Feature
            icon={Target}
            delay={0}
            title="Service-name correlation"
            text="Tracks threats by stable container identity and network alias — survives restarts, scaling, redeploys. No IP churn = no false negatives."
          />
          <Feature
            icon={GitBranch}
            delay={1}
            title="Kill-chain reconstruction"
            text="Stitches east–west movement across services into a single incident with ordered steps, MITRE techniques, and service path."
          />
          <Feature
            icon={Network}
            delay={2}
            title="Live dependency graph"
            text="Topology collector discovers every container + edge. Attack paths overlay on the live graph with a replay animation."
          />
          <Feature
            icon={Layers}
            delay={3}
            title="Multi-layer signals"
            text="Network packets + HTTP APIs + auth events fused in one correlation engine — not three siloed tools you stitch together."
          />
          <Feature
            icon={Boxes}
            delay={4}
            title="MITRE ATT&CK for Containers"
            text="Every incident is mapped to techniques in the Containers matrix. Coverage view shows what you detect vs. what you're blind to."
          />
          <Feature
            icon={Gauge}
            delay={5}
            title="Real-time risk scoring"
            text="Per-service risk decays without signal, spikes on evidence. Heatmap surfaces critical entities before the analyst has to look."
          />
        </div>
      </section>

      {/* ----------------------------- ACHIEVEMENTS ----------------------------- */}
      <section className="space-y-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.03] p-6 md:p-8">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400">
            What we achieved
          </h2>
        </div>
        <h3 className="max-w-3xl text-2xl font-bold leading-tight text-base-100 md:text-3xl">
          Measured end-to-end. Not a marketing claim.
        </h3>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-base-800 bg-base-950/60 p-5">
            <Clock className="mb-3 h-5 w-5 text-emerald-400" />
            <div className="text-2xl font-bold text-base-100">6.0 – 8.1 s</div>
            <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              Mean time to detect
            </div>
            <div className="mt-2 text-[11px] text-base-500 leading-relaxed">
              From first attack event to kill-chain alert, across all three formal scenarios. Raw-log baseline: 199–247 s.
            </div>
          </div>
          <div className="rounded-lg border border-base-800 bg-base-950/60 p-5">
            <Zap className="mb-3 h-5 w-5 text-emerald-400" />
            <div className="text-2xl font-bold text-base-100">≥ 95 %</div>
            <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              MTTD reduction vs. raw logs
            </div>
            <div className="mt-2 text-[11px] text-base-500 leading-relaxed">
              Scenario A: 97.57 %. Scenario B: 95.91 %. Measured under controlled trials, 3 runs each, reproducible via{' '}
              <code className="rounded bg-base-900 px-1 font-mono">make evaluate-full</code>.
            </div>
          </div>
          <div className="rounded-lg border border-base-800 bg-base-950/60 p-5">
            <Activity className="mb-3 h-5 w-5 text-emerald-400" />
            <div className="text-2xl font-bold text-base-100">99.97 %</div>
            <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              Alert reduction ratio
            </div>
            <div className="mt-2 text-[11px] text-base-500 leading-relaxed">
              12,847 raw events collapsed into 3 correlated incidents in the reference run. Analysts stop triaging noise.
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-base-800 bg-base-950/40 p-4">
            <div className="text-sm font-semibold text-base-100">0 false positives</div>
            <div className="mt-1 text-[11px] text-base-500">
              Benign-traffic scenario: 3 runs × 0 incidents raised. Correlation rules hold under load.
            </div>
          </div>
          <div className="rounded-lg border border-base-800 bg-base-950/40 p-4">
            <div className="text-sm font-semibold text-base-100">100 % detection rate</div>
            <div className="mt-1 text-[11px] text-base-500">
              Every crafted attack scenario — SQLi, path traversal, credential stuffing, lateral pivot — produced a correctly-typed incident.
            </div>
          </div>
          <div className="rounded-lg border border-base-800 bg-base-950/40 p-4">
            <div className="text-sm font-semibold text-base-100">One-command demo</div>
            <div className="mt-1 text-[11px] text-base-500">
              <code className="rounded bg-base-900 px-1 font-mono text-[10px]">make start</code> → full Docker stack.{' '}
              <code className="rounded bg-base-900 px-1 font-mono text-[10px]">make attack-a</code> → watch it fire live.
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------- COMPARISON ----------------------------- */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-accent" />
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            Why it matters
          </h2>
        </div>
        <h3 className="max-w-3xl text-2xl font-bold leading-tight text-base-100 md:text-3xl">
          What incumbents miss — and what we catch.
        </h3>
        <div className="overflow-hidden rounded-lg border border-base-800 bg-base-900/40">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-base-800 bg-base-950/60">
                <th className="py-2.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-base-500">Capability</th>
                <th className="py-2.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-base-500">Splunk · Wazuh · Elastic</th>
                <th className="py-2.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-accent">SecuriSphere</th>
              </tr>
            </thead>
            <tbody>
              <CompareRow what="Service-name-aware correlation (no IP churn)" legacy="IP-based only" us="native" highlight />
              <CompareRow what="Kill-chain reconstruction across services" legacy="not supported" us="first-class" highlight />
              <CompareRow what="Live service dependency graph" legacy="external tooling" us="built-in" />
              <CompareRow what="Network + API + auth in one engine" legacy="3 separate tools" us="unified" />
              <CompareRow what="MITRE ATT&CK for Containers coverage view" legacy="partial / missing" us="mapped" />
              <CompareRow what="Measured MTTD end-to-end" legacy="not reported" us="6–8 s" />
              <CompareRow what="One-command demo with attack simulator" legacy="—" us="make start" />
            </tbody>
          </table>
        </div>
      </section>

      {/* ----------------------------- CTA ----------------------------- */}
      <section className="flex flex-col items-start gap-4 rounded-2xl border border-accent/25 bg-gradient-to-br from-accent/[0.06] via-base-900 to-base-950 p-6 md:flex-row md:items-center md:justify-between md:p-8">
        <div className="max-w-xl">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">Ready to see it fire?</div>
          <div className="mt-2 text-xl font-bold text-base-100 md:text-2xl">
            Launch an attack. Watch the kill chain replay on the graph.
          </div>
          <p className="mt-2 text-sm text-base-400">
            The console is wired to live data. Open the dashboard, pick an incident, and the topology auto-plays the attack step by step.
          </p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
          <Link
            to="/dashboard"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-accent/40 bg-accent/20 px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-accent/30"
          >
            <Play className="h-4 w-4" fill="currentColor" />
            Open dashboard
          </Link>
          <Link
            to="/incidents"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-base-700 bg-base-900/60 px-4 py-2 text-sm text-base-200 transition-colors hover:bg-base-800"
          >
            <AlertTriangle className="h-4 w-4" />
            View incidents
          </Link>
          <Link
            to="/mitre"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-base-700 bg-base-900/60 px-4 py-2 text-sm text-base-200 transition-colors hover:bg-base-800"
          >
            <Shield className="h-4 w-4" />
            MITRE coverage
          </Link>
        </div>
      </section>
    </motion.div>
  );
}
