import { Wifi, WifiOff } from 'lucide-react';

export default function StatusBar({ connected, lastUpdate, eventCount = 0, incidentCount = 0, usingMock }) {
  return (
    <footer className="flex h-7 shrink-0 items-center justify-between border-t border-base-800 bg-base-900 px-6 font-mono text-[10px] text-base-500 transition-colors duration-200">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          {connected ? (
            <Wifi className="h-3 w-3 text-base-400" />
          ) : (
            <WifiOff className="h-3 w-3 text-base-600" />
          )}
          {connected ? 'WebSocket connected' : 'Disconnected — polling'}
        </span>
        {usingMock && <span className="text-base-500">Mock data</span>}
      </div>

      <span>
        {eventCount} events &middot; {incidentCount} incidents
      </span>

      <span>
        SecuriSphere v2.0 &middot; Last sync:{' '}
        {lastUpdate ? `${Math.floor((Date.now() - new Date(lastUpdate).getTime()) / 1000)}s ago` : 'pending'}
      </span>
    </footer>
  );
}
