import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { api } from '@/lib/api';

const SCENARIO_LABELS = {
  a: 'Scenario A — Brute Force → Credential Compromise → Data Exfiltration',
  b: 'Scenario B — Recon → SQL Injection → Privilege Escalation',
  c: 'Scenario C — Multi-Hop Lateral Movement',
};

function normalizeScenario(raw) {
  if (!raw) return null;
  const s = String(raw).trim().toLowerCase();
  if (s.startsWith('a') || s.includes('brute')) return 'a';
  if (s.startsWith('b') || s.includes('sql') || s.includes('recon')) return 'b';
  if (s.startsWith('c') || s.includes('lateral')) return 'c';
  return s;
}

/**
 * Banner shown on dashboard when a demo scenario is active.
 * Polls /api/demo-status every 3s.
 */
export default function DemoBanner() {
  const [state, setState] = useState({ active: false, scenario: null });

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const data = await api.getDemoStatus();
        if (!cancelled) {
          setState({
            active: Boolean(data?.active),
            scenario: normalizeScenario(data?.scenario),
          });
        }
      } catch {
        if (!cancelled) setState({ active: false, scenario: null });
      }
    }

    poll();
    const id = window.setInterval(poll, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const visible = state.active && state.scenario;
  const label = visible
    ? SCENARIO_LABELS[state.scenario] || `Active scenario: ${state.scenario}`
    : '';

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="demo-banner"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.25 }}
          role="status"
          aria-live="polite"
          className="flex items-center gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-200 shadow-sm"
        >
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-400" />
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-amber-300/80">
            Live demo
          </span>
          <span className="flex-1 font-medium">{label}</span>
          <span className="rounded border border-amber-500/30 px-2 py-0.5 font-mono text-[10px] text-amber-300">
            ATTACK IN PROGRESS
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
