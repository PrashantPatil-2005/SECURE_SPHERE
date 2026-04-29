import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';

const SCENARIOS = [
  {
    id: 'a',
    title: 'Scenario A — Brute Force → Exfil',
    blurb: '4-stage credential kill chain against auth-service.',
    stages: [
      'Recon: probe /auth endpoints',
      'Brute force login (50 attempts)',
      'Credential reuse on API',
      'Data exfiltration over HTTPS',
    ],
    mitre: ['T1595', 'T1110', 'T1078', 'T1041'],
    accent: 'border-red-500/50 bg-red-500/[0.06]',
    pill: 'bg-red-500/20 text-red-300 border-red-500/40',
  },
  {
    id: 'b',
    title: 'Scenario B — Recon → SQLi → PrivEsc',
    blurb: 'Web exploit kill chain against the public web-app.',
    stages: [
      'Port scan + service fingerprint',
      'SQL injection on /search',
      'Privilege escalation via CVE',
      'Lateral movement attempt',
    ],
    mitre: ['T1046', 'T1190', 'T1068', 'T1021'],
    accent: 'border-amber-500/50 bg-amber-500/[0.06]',
    pill: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  },
  {
    id: 'c',
    title: 'Scenario C — Multi-Hop Lateral',
    blurb: 'Cloud-style lateral movement + bulk data theft.',
    stages: [
      'Initial foothold (stolen key)',
      'Lateral: db-host → api-host',
      'Discovery: files + mounted volumes',
      'Bulk exfil over alt-proto',
    ],
    mitre: ['T1021', 'T1083', 'T1530', 'T1048'],
    accent: 'border-cyan-500/50 bg-cyan-500/[0.06]',
    pill: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
  },
];

const TARGET_KEYS = ['auth-service', 'api-gateway', 'payment-service'];

function TargetBar() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const s = await api.getSystemStatus();
        if (!stop) setStatus(s || {});
      } catch {
        if (!stop) setStatus({});
      }
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => { stop = true; clearInterval(id); };
  }, []);

  const chip = (key) => {
    const up = status && (status.services?.[key]?.up ?? status.containers?.[key]?.up ?? status.monitors?.[key]?.active ?? true);
    const color = up ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-zinc-700/40 text-zinc-400 border-zinc-700';
    return (
      <span key={key} className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-[11px] ${color}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${up ? 'bg-emerald-400' : 'bg-zinc-500'}`} />
        {key}
      </span>
    );
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded border border-zinc-800 bg-zinc-950/60 px-3 py-2">
      <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Targets</span>
      {TARGET_KEYS.map(chip)}
    </div>
  );
}

function ScenarioCard({ s, running, currentScenario, onLaunch, speed }) {
  const isThis = running && currentScenario === s.id;
  const disabled = running;
  return (
    <div className={`flex flex-col gap-3 rounded-lg border p-4 ${s.accent}`}>
      <div>
        <div className="font-mono text-sm font-semibold text-zinc-100">{s.title}</div>
        <div className="mt-1 text-xs text-zinc-400">{s.blurb}</div>
      </div>
      <ol className="flex flex-col gap-1 text-[11px] text-zinc-300">
        {s.stages.map((st, i) => (
          <li key={i} className="flex gap-2">
            <span className="font-mono text-zinc-500">{i + 1}.</span>
            <span>{st}</span>
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-1">
        {s.mitre.map((m) => (
          <span key={m} className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${s.pill}`}>{m}</span>
        ))}
      </div>
      <button
        onClick={() => onLaunch(s.id, speed)}
        disabled={disabled}
        className={`mt-auto rounded border px-3 py-2 font-mono text-xs font-semibold uppercase tracking-wider transition-colors ${
          disabled
            ? 'cursor-not-allowed border-zinc-800 bg-zinc-900 text-zinc-600'
            : 'border-red-500/60 bg-red-500/10 text-red-300 hover:bg-red-500/25'
        }`}
      >
        {isThis ? '● Running…' : '▶ Launch'}
      </button>
    </div>
  );
}

function TerminalLog({ lines, running, scenario }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines]);
  return (
    <div className="rounded-lg border border-zinc-800 bg-black">
      <div className="flex items-center justify-between border-b border-zinc-800 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <span className="ml-2 font-mono text-[11px] text-zinc-500">attacker@securisphere:~$</span>
        </div>
        <div className="font-mono text-[10px] text-zinc-500">
          {running ? <span className="text-red-400">● running {scenario}</span> : <span>idle</span>}
        </div>
      </div>
      <pre
        ref={ref}
        className="m-0 h-[360px] overflow-auto p-3 font-mono text-[11px] leading-relaxed text-green-300/90"
      >
        {lines.length === 0
          ? '// waiting for launch…\n'
          : lines.join('\n') + '\n'}
      </pre>
    </div>
  );
}

export default function Attacker() {
  const [speed, setSpeed] = useState('demo');
  const [status, setStatus] = useState({ running: false, scenario: null, log_lines: [] });
  const [err, setErr] = useState('');

  useEffect(() => {
    let stop = false;
    let timer = null;
    let delay = 1000;
    const MIN = 1000;
    const MAX = 15000;

    const tick = async () => {
      if (stop) return;
      try {
        const s = await api.getAttackStatus();
        if (stop) return;
        setStatus(s || {});
        delay = MIN;
      } catch {
        delay = Math.min(delay * 2, MAX);
      } finally {
        if (!stop) timer = setTimeout(tick, delay);
      }
    };
    tick();
    return () => { stop = true; if (timer) clearTimeout(timer); };
  }, []);

  const handleLaunch = async (scenario, spd) => {
    setErr('');
    try {
      const res = await api.runAttack(scenario, spd);
      if (res?.status === 'error' || res?.status === 'busy') {
        setErr(res.message || 'launch failed');
      }
    } catch (e) {
      setErr(String(e?.message || e));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-black to-red-950/40 text-zinc-100">
      <header className="border-b border-red-900/40 bg-black/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚔</span>
            <div>
              <h1 className="font-mono text-lg font-bold tracking-tight text-red-300">
                SecuriSphere Attack Console
              </h1>
              <p className="text-[11px] text-zinc-500">
                Red team operations · isolated from the SOC dashboard
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Speed</label>
            <select
              value={speed}
              onChange={(e) => setSpeed(e.target.value)}
              className="rounded border border-zinc-800 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-200"
            >
              <option value="demo">demo</option>
              <option value="normal">normal</option>
              <option value="fast">fast</option>
            </select>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-5 px-6 py-6">
        <TargetBar />

        {err && (
          <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 font-mono text-xs text-red-300">
            {err}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {SCENARIOS.map((s) => (
            <ScenarioCard
              key={s.id}
              s={s}
              running={status.running}
              currentScenario={status.scenario}
              onLaunch={handleLaunch}
              speed={speed}
            />
          ))}
        </div>

        <div className="flex items-center justify-between">
          <div className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Live Log</div>
          <button
            onClick={() => handleLaunch('all', speed)}
            disabled={status.running}
            className={`rounded border px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider transition-colors ${
              status.running
                ? 'cursor-not-allowed border-zinc-800 bg-zinc-900 text-zinc-600'
                : 'border-red-500/60 bg-red-500/10 text-red-300 hover:bg-red-500/25'
            }`}
          >
            ▶▶ Run All
          </button>
        </div>

        <TerminalLog lines={status.log_lines || []} running={status.running} scenario={status.scenario} />

        <footer className="pt-2 text-center font-mono text-[10px] text-zinc-600">
          Attacks originate from this console only · SOC lives at{' '}
          <a href="/" className="text-zinc-400 hover:text-red-300">/</a>
        </footer>
      </main>
    </div>
  );
}
