import { cn } from '@/lib/utils';
import { Wifi, WifiOff } from 'lucide-react';

export default function StatusBar({ connected, lastUpdate, eventCount = 0, incidentCount = 0, usingMock }) {
  return (
    <footer className="h-7 flex items-center justify-between px-6 border-t border-white/[0.05] bg-base-900 text-[10px] font-mono text-base-500 shrink-0">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          {connected ? <Wifi className="w-3 h-3 text-green-500" /> : <WifiOff className="w-3 h-3 text-red-400" />}
          {connected ? 'WebSocket connected' : 'Disconnected — polling'}
        </span>
        {usingMock && (
          <span className="text-yellow-500">Mock data</span>
        )}
      </div>

      <span>
        {eventCount} events &middot; {incidentCount} incidents
      </span>

      <span>
        SecuriSphere v2.0 &middot; Last sync: {lastUpdate ? `${Math.floor((Date.now() - new Date(lastUpdate).getTime()) / 1000)}s ago` : 'pending'}
      </span>
    </footer>
  );
}
