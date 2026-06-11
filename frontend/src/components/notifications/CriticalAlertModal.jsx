import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ShieldAlert, Volume2, VolumeX, X } from 'lucide-react';
import { useAppStore } from '@/stores/useAppStore';
import { getSeverityString, safeString, isCorrelatedIncident, parseServerTime } from '@/lib/utils';

const AUTO_DISMISS_MS = 6000;
// On first mount, kill-chain incidents within this window still fire — the
// user likely just came from /attacker (outside auth shell where this modal
// isn't mounted) so the chain was emitted while we were unmounted.
const FIRST_MOUNT_FRESH_MS = 60_000;

function severityRing(sev) {
  switch (sev) {
    case 'critical': return 'border-red-500/70 shadow-[0_0_60px_rgba(239,68,68,0.45)]';
    case 'high':     return 'border-orange-500/70 shadow-[0_0_50px_rgba(249,115,22,0.4)]';
    default:         return 'border-amber-500/60 shadow-[0_0_40px_rgba(251,191,36,0.3)]';
  }
}

function severityText(sev) {
  switch (sev) {
    case 'critical': return 'text-red-300';
    case 'high':     return 'text-orange-300';
    default:         return 'text-amber-300';
  }
}

// Synthesize an alert beep with Web Audio API. No external asset.
// Two short rising tones + decay envelope.
function playAlertBeep(volume = 0.6) {
  if (typeof window === 'undefined') return;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  let ctx;
  try { ctx = new Ctx(); } catch { return; }

  const now = ctx.currentTime;
  const master = ctx.createGain();
  master.gain.value = Math.max(0, Math.min(1, volume));
  master.connect(ctx.destination);

  const tone = (freq, start, dur) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, now + start);
    gain.gain.setValueAtTime(0, now + start);
    gain.gain.linearRampToValueAtTime(0.9, now + start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + start + dur);
    osc.connect(gain).connect(master);
    osc.start(now + start);
    osc.stop(now + start + dur + 0.02);
  };

  tone(880, 0,    0.18);
  tone(1320, 0.22, 0.22);

  // Auto-close context after sounds finish.
  setTimeout(() => { try { ctx.close(); } catch { /* ignore */ } }, 900);
}

export default function CriticalAlertModal({ incidents = [] }) {
  const navigate = useNavigate();
  const seenRef = useRef(new Set());
  const initRef = useRef(false);
  const [queue, setQueue] = useState([]);
  const soundEnabled = useAppStore((s) => s.soundEnabled);
  const soundVolume = useAppStore((s) => s.soundVolume);
  const toggleSound = useAppStore((s) => s.toggleSound);

  // Detect kill-chain incidents — both new pushes and recent kill chains
  // present at first mount (covers /attacker → dashboard navigation).
  useEffect(() => {
    const now = Date.now();
    const firstMount = !initRef.current;
    const fresh = [];
    for (const inc of incidents) {
      const id = inc?.incident_id;
      if (!id || seenRef.current.has(id)) continue;
      const isChain = isCorrelatedIncident(inc);

      if (firstMount && !isChain) {
        // Non-chain: mark seen so a refresh doesn't replay old toasts via the
        // modal path. Toaster handles its own first-mount muting.
        seenRef.current.add(id);
        continue;
      }
      if (firstMount && isChain) {
        // Only fire if recent — old chains from previous sessions stay quiet.
        // Backend emits naive UTC ISO; parseServerTime appends Z so JS doesn't
        // mis-interpret it as local time.
        const d = parseServerTime(inc.detected_at || inc.created_at || inc.first_event_at || inc.timestamp);
        const ts = d ? d.getTime() : 0;
        if (!ts || now - ts > FIRST_MOUNT_FRESH_MS) {
          seenRef.current.add(id);
          continue;
        }
      }

      seenRef.current.add(id);
      if (!isChain) continue;

      fresh.push({
        id,
        severity: getSeverityString(inc.severity).toLowerCase(),
        type: safeString(inc.incident_type),
        path: inc.service_path || [],
        techniques: inc.mitre_techniques || [],
        confidence: (inc.confidence || {}).posterior,
        mttd: inc.mttd_seconds,
        ts: now,
      });
    }
    initRef.current = true;
    if (fresh.length) setQueue((q) => [...q, ...fresh]);
  }, [incidents]);

  const current = queue[0];

  // Play sound when a new modal becomes current.
  useEffect(() => {
    if (!current) return;
    if (soundEnabled) playAlertBeep(soundVolume);
    const t = setTimeout(() => {
      setQueue((q) => q.slice(1));
    }, AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [current?.id, soundEnabled, soundVolume]);

  // ESC dismisses.
  useEffect(() => {
    if (!current) return;
    const onKey = (e) => {
      if (e.key === 'Escape') setQueue((q) => q.slice(1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [current]);

  const dismiss = () => setQueue((q) => q.slice(1));
  const inspect = () => { dismiss(); navigate('/incidents'); };
  const replay = () => { dismiss(); navigate('/replay'); };

  return (
    <AnimatePresence>
      {current && (
        <motion.div
          key={current.id}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
          onClick={dismiss}
        >
          <motion.div
            initial={{ scale: 0.85, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.92, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.34, 1.56, 0.64, 1] }}
            onClick={(e) => e.stopPropagation()}
            className={`relative w-full max-w-[480px] rounded-2xl border-2 bg-base-900/95 p-7 ${severityRing(current.severity)}`}
          >
            <span className={`pointer-events-none absolute inset-0 rounded-2xl border-2 ${severityRing(current.severity)} animate-pulse-glow`} />

            <button
              onClick={dismiss}
              className="absolute right-3 top-3 rounded-md p-1 text-base-500 hover:bg-white/5 hover:text-base-200 transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>

            <button
              onClick={toggleSound}
              className="absolute right-10 top-3 rounded-md p-1 text-base-500 hover:bg-white/5 hover:text-base-200 transition-colors"
              aria-label={soundEnabled ? 'Mute alert sound' : 'Unmute alert sound'}
              title={soundEnabled ? 'Mute alert sound' : 'Unmute alert sound'}
            >
              {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            <div className="flex flex-col items-center text-center">
              <div className={`flex h-16 w-16 items-center justify-center rounded-full border-2 ${severityRing(current.severity)} mb-4`}>
                {current.severity === 'critical'
                  ? <ShieldAlert className={`w-8 h-8 ${severityText(current.severity)}`} />
                  : <AlertTriangle className={`w-8 h-8 ${severityText(current.severity)}`} />}
              </div>

              <p className={`text-[10px] font-bold uppercase tracking-[0.25em] ${severityText(current.severity)}`}>
                {current.severity} · incident
              </p>
              <h2 className="mt-2 text-xl font-bold text-base-100 tracking-tight">
                {(current.type || 'Security incident').replace(/_/g, ' ')}
              </h2>

              {current.path?.length ? (
                <p className="mt-3 font-mono text-xs text-base-300 break-all">
                  {current.path.join(' → ')}
                </p>
              ) : null}

              {current.techniques?.length ? (
                <div className="mt-3 flex flex-wrap justify-center gap-1.5">
                  {current.techniques.slice(0, 6).map((t) => (
                    <span key={t} className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-base-300">
                      {t}
                    </span>
                  ))}
                </div>
              ) : null}

              <div className="mt-4 flex items-center gap-4 text-[11px] text-base-400">
                {typeof current.confidence === 'number' && (
                  <span>conf <span className="font-mono text-base-200">{(current.confidence * 100).toFixed(0)}%</span></span>
                )}
                {typeof current.mttd === 'number' && (
                  <span>MTTD <span className="font-mono text-base-200">{current.mttd.toFixed(1)}s</span></span>
                )}
              </div>

              <div className="mt-6 flex w-full gap-2">
                <button
                  onClick={replay}
                  className="flex-1 h-9 rounded-lg border border-white/10 bg-white/5 text-sm font-medium text-base-200 hover:bg-white/10 transition-colors"
                >
                  Replay
                </button>
                <button
                  onClick={inspect}
                  className="flex-1 h-9 rounded-lg bg-accent text-sm font-semibold text-white hover:bg-accent-hover transition-colors"
                >
                  Acknowledge
                </button>
              </div>

              {queue.length > 1 && (
                <p className="mt-3 text-[10px] uppercase tracking-widest text-base-500">
                  +{queue.length - 1} more pending
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
