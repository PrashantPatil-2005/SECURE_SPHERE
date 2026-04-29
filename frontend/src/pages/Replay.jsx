import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';

// Threat Cinema — scrub through the frames the engine recorded as the
// incident formed. Each frame is one timestep. Autoplay reads them at
// 1 frame/second; manual mode uses the slider.

function frameSummary(frame) {
  if (!frame) return null;
  const ev = frame.event || {};
  const cumulative = frame.cumulative || {};
  return {
    eventType: ev.event_type,
    service: ev.source_service_name,
    severity: ev.severity,
    rule: frame.rule,
    delta: frame.delta || {},
    path: cumulative.service_path || [],
    techniques: cumulative.mitre_techniques || [],
    stepCount: cumulative.step_count || 0,
  };
}

function severityBadge(sev) {
  const cls = sev === 'critical' ? 'bg-red-600/20 text-red-300 border-red-700'
            : sev === 'high'     ? 'bg-orange-600/20 text-orange-300 border-orange-700'
            : sev === 'medium'   ? 'bg-amber-600/20 text-amber-300 border-amber-700'
            : 'bg-slate-700/40 text-slate-200 border-slate-600';
  return <span className={`px-2 py-0.5 rounded border text-xs font-mono ${cls}`}>{sev || '—'}</span>;
}

export default function Replay() {
  const [replays, setReplays] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [frames, setFrames] = useState([]);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(1000);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  // Load replay index
  useEffect(() => {
    let cancel = false;
    api.getReplaysIndex()
      .then((data) => {
        if (cancel) return;
        const list = Array.isArray(data) ? data : [];
        setReplays(list);
        if (list.length && !selectedId) setSelectedId(list[0].incident_id);
      })
      .catch((e) => setError(String(e)));
    return () => { cancel = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load frames for selected
  useEffect(() => {
    if (!selectedId) return;
    let cancel = false;
    api.getReplayFrames(selectedId)
      .then((data) => {
        if (cancel) return;
        const list = Array.isArray(data) ? data : [];
        setFrames(list);
        setStep(0);
      })
      .catch((e) => setError(String(e)));
    return () => { cancel = true; };
  }, [selectedId]);

  // Autoplay timer
  useEffect(() => {
    if (!playing || frames.length === 0) return;
    timerRef.current = setInterval(() => {
      setStep((s) => {
        if (s >= frames.length - 1) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, speedMs);
    return () => clearInterval(timerRef.current);
  }, [playing, speedMs, frames.length]);

  const current = frames[step];
  const summary = useMemo(() => frameSummary(current), [current]);

  if (error && replays.length === 0) {
    return (
      <div className="p-6 text-sm text-red-300">
        Replay engine error: {error}
      </div>
    );
  }
  if (replays.length === 0) {
    return (
      <div className="p-6 text-sm text-slate-400">
        No incidents recorded yet. Run an attack scenario, then come back.
      </div>
    );
  }

  return (
    <div className="p-6 grid grid-cols-12 gap-4">
      {/* Replay list */}
      <aside className="col-span-3 space-y-2">
        <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Replays</div>
        {replays.map((r) => (
          <button
            key={r.incident_id}
            onClick={() => { setPlaying(false); setSelectedId(r.incident_id); }}
            className={`block w-full text-left px-3 py-2 rounded border ${
              r.incident_id === selectedId
                ? 'border-cyan-500 bg-cyan-500/10 text-cyan-100'
                : 'border-slate-700 bg-slate-900/40 text-slate-300 hover:border-slate-500'
            }`}
          >
            <div className="font-mono text-xs truncate">{r.incident_id}</div>
            <div className="text-[10px] text-slate-500">
              {r.first_frame_ts ? new Date(r.first_frame_ts * 1000).toLocaleString() : ''}
            </div>
          </button>
        ))}
      </aside>

      {/* Cinema */}
      <main className="col-span-9 space-y-4">
        <header className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-500">Incident</div>
            <div className="font-mono text-sm text-slate-200">{selectedId}</div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPlaying((p) => !p)}
              className="px-3 py-1.5 rounded border border-slate-600 bg-slate-800 text-sm hover:bg-slate-700"
            >
              {playing ? 'Pause' : 'Play'}
            </button>
            <select
              value={speedMs}
              onChange={(e) => setSpeedMs(Number(e.target.value))}
              className="px-2 py-1.5 rounded border border-slate-600 bg-slate-800 text-sm text-slate-200"
            >
              <option value={2000}>0.5×</option>
              <option value={1000}>1×</option>
              <option value={500}>2×</option>
              <option value={250}>4×</option>
            </select>
          </div>
        </header>

        {/* Scrub bar */}
        <div className="bg-slate-900/40 border border-slate-700 rounded p-3">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>frame {step + 1} / {frames.length || 1}</span>
            <span>{summary?.path?.length || 0} services touched</span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            value={step}
            onChange={(e) => { setPlaying(false); setStep(Number(e.target.value)); }}
            className="w-full"
          />
        </div>

        {/* Current frame card */}
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="bg-slate-900/60 border border-slate-700 rounded p-4"
        >
          {summary ? (
            <>
              <div className="flex items-center gap-3 mb-2">
                {severityBadge(summary.severity)}
                <div className="text-base font-semibold text-slate-100">
                  {summary.eventType || '—'}
                </div>
                <div className="text-xs text-slate-400 ml-auto">
                  rule: <span className="font-mono">{summary.rule || '—'}</span>
                </div>
              </div>
              <div className="text-sm text-slate-300">
                Origin service: <span className="font-mono">{summary.service || '—'}</span>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs uppercase text-slate-500 mb-1">Service path so far</div>
                  <div className="text-sm font-mono text-cyan-200 break-all">
                    {summary.path.length ? summary.path.join(' → ') : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase text-slate-500 mb-1">MITRE techniques</div>
                  <div className="text-sm font-mono text-fuchsia-200">
                    {summary.techniques.length ? summary.techniques.join(', ') : '—'}
                  </div>
                </div>
              </div>

              {(summary.delta?.new_services?.length || summary.delta?.new_techniques?.length) ? (
                <div className="mt-3 text-xs text-emerald-300 font-mono">
                  {summary.delta.new_services?.length
                    ? `+ services: ${summary.delta.new_services.join(', ')}` : ''}
                  {summary.delta.new_techniques?.length
                    ? `   + techniques: ${summary.delta.new_techniques.join(', ')}` : ''}
                </div>
              ) : null}
            </>
          ) : (
            <div className="text-sm text-slate-400">No frame at this step.</div>
          )}
        </motion.div>
      </main>
    </div>
  );
}
