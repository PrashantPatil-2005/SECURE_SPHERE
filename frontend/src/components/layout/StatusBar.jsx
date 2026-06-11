import { useState, useEffect } from 'react';
import { WifiOff, Activity, AlertCircle } from 'lucide-react';

function formatSince(lastUpdate) {
  if (!lastUpdate) return '—';
  const sinceSeconds = Math.floor((Date.now() - new Date(lastUpdate).getTime()) / 1000);
  if (sinceSeconds < 5) return 'just now';
  if (sinceSeconds < 60) return `${sinceSeconds}s ago`;
  return `${Math.floor(sinceSeconds / 60)}m ago`;
}

export default function StatusBar({ connected, lastUpdate, eventCount = 0, incidentCount = 0 }) {
  const [sinceLabel, setSinceLabel] = useState(() => formatSince(lastUpdate));

  useEffect(() => {
    setSinceLabel(formatSince(lastUpdate));
    const id = setInterval(() => setSinceLabel(formatSince(lastUpdate)), 1000);
    return () => clearInterval(id);
  }, [lastUpdate]);

  return (
    <footer className="flex h-7 shrink-0 items-center justify-between border-t border-base-800 bg-base-950 px-5 text-2xs text-base-600 transition-colors duration-200">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5">
          {connected ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
              <span className="font-medium text-base-500">Live</span>
            </>
          ) : (
            <>
              <WifiOff className="h-3 w-3 text-base-700" />
              <span>Offline — polling</span>
            </>
          )}
        </span>

        <span className="text-base-800" aria-hidden="true">·</span>

        <span className="flex items-center gap-1">
          <Activity className="h-3 w-3 shrink-0" />
          <span className="type-data text-2xs text-base-500">{eventCount.toLocaleString()}</span>
        </span>

        <span className="flex items-center gap-1">
          <AlertCircle className="h-3 w-3 shrink-0" />
          <span className="type-data text-2xs text-base-500">{incidentCount}</span>
        </span>
      </div>

      <span className="hidden font-medium tracking-[0.04em] text-base-700 sm:inline">
        SecuriSphere
      </span>

      <span className="type-data text-2xs text-base-600">
        sync {sinceLabel}
      </span>
    </footer>
  );
}
