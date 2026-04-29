import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const MAX_VISIBLE = 4;
const AUTO_DISMISS_MS = 7000;

function severityClasses(sev) {
  switch (sev) {
    case 'critical':
      return 'border-red-500/70 bg-red-950/85 text-red-100 shadow-red-900/40';
    case 'high':
      return 'border-orange-500/70 bg-orange-950/85 text-orange-100 shadow-orange-900/40';
    case 'medium':
      return 'border-amber-500/70 bg-amber-950/85 text-amber-100 shadow-amber-900/40';
    default:
      return 'border-cyan-500/70 bg-slate-900/90 text-slate-100 shadow-cyan-900/30';
  }
}

function toShortType(s) {
  if (!s) return 'incident';
  return String(s).replace(/_/g, ' ');
}

export default function IncidentToaster({ incidents = [] }) {
  const navigate = useNavigate();
  const seenRef = useRef(new Set());
  const initRef = useRef(false);
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    // First pass: mark every existing incident seen so a refresh doesn't
    // spam the user with stale toasts. Only NEW incident_ids fire after.
    if (!initRef.current) {
      for (const inc of incidents) {
        if (inc?.incident_id) seenRef.current.add(inc.incident_id);
      }
      initRef.current = true;
      return;
    }

    const fresh = [];
    for (const inc of incidents) {
      const id = inc?.incident_id;
      if (!id || seenRef.current.has(id)) continue;
      seenRef.current.add(id);
      fresh.push({
        id,
        severity:    inc.severity,
        type:        inc.incident_type,
        path:        inc.service_path || [],
        confidence:  (inc.confidence || {}).posterior,
        techniques:  inc.mitre_techniques || [],
        ts:          Date.now(),
      });
    }
    if (fresh.length === 0) return;
    setToasts((prev) => [...fresh, ...prev].slice(0, 8));
  }, [incidents]);

  // Auto-dismiss
  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) =>
      setTimeout(() => {
        setToasts((prev) => prev.filter((p) => p.id !== t.id));
      }, AUTO_DISMISS_MS - (Date.now() - t.ts))
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts]);

  const dismiss = (id) => setToasts((prev) => prev.filter((p) => p.id !== id));

  const visible = toasts.slice(0, MAX_VISIBLE);

  return (
    <div className="pointer-events-none fixed right-4 top-16 z-[1000] flex w-[360px] flex-col gap-2">
      <AnimatePresence initial={false}>
        {visible.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, x: 60, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 60, scale: 0.95 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className={`pointer-events-auto rounded-md border px-3 py-2.5 shadow-xl backdrop-blur ${severityClasses(t.severity)}`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 h-2 w-2 shrink-0 animate-pulse rounded-full bg-current" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider opacity-80">
                    {t.severity || 'incident'} · {toShortType(t.type)}
                  </div>
                  <button
                    onClick={() => dismiss(t.id)}
                    className="text-xs opacity-60 hover:opacity-100"
                    aria-label="dismiss"
                  >
                    ×
                  </button>
                </div>
                <div className="mt-1 truncate font-mono text-xs opacity-90">
                  {t.path.length ? t.path.join(' → ') : '—'}
                </div>
                {t.techniques?.length ? (
                  <div className="mt-1 truncate text-[11px] font-mono opacity-70">
                    {t.techniques.slice(0, 4).join(' · ')}
                  </div>
                ) : null}
                <div className="mt-2 flex items-center justify-between gap-2">
                  <div className="text-[11px] opacity-70">
                    {typeof t.confidence === 'number'
                      ? `conf ${(t.confidence * 100).toFixed(0)}%`
                      : ''}
                  </div>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => { dismiss(t.id); navigate('/replay'); }}
                      className="rounded border border-current/40 bg-black/30 px-2 py-0.5 text-[11px] hover:bg-black/50"
                    >
                      Replay
                    </button>
                    <button
                      onClick={() => { dismiss(t.id); navigate('/incidents'); }}
                      className="rounded border border-current/40 bg-black/30 px-2 py-0.5 text-[11px] hover:bg-black/50"
                    >
                      Inspect
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
      {toasts.length > MAX_VISIBLE ? (
        <div className="pointer-events-auto self-end rounded border border-slate-600 bg-slate-900/80 px-2 py-0.5 text-[11px] text-slate-300">
          +{toasts.length - MAX_VISIBLE} more
        </div>
      ) : null}
    </div>
  );
}
