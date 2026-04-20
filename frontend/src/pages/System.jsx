import { useState } from 'react';
import { motion } from 'framer-motion';
import { Server, Webhook, ExternalLink } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

export default function System({ systemStatus = {}, onRefresh }) {
  const [webhook, setWebhook] = useState('');

  const services = [];
  if (systemStatus?.redis) {
    services.push({
      name: 'redis-cache',
      status: systemStatus.redis.connected ? 'running' : 'stopped',
      detail: systemStatus.redis.ping,
    });
  }
  if (systemStatus?.correlation_engine) {
    services.push({
      name: 'correlation-engine',
      status: systemStatus.correlation_engine.active ? 'running' : 'stopped',
      incidents: systemStatus.correlation_engine.incidents,
      error: systemStatus.correlation_engine.error,
    });
  }
  if (systemStatus?.monitors) {
    for (const [k, v] of Object.entries(systemStatus.monitors)) {
      services.push({
        name: `${k}-monitor`,
        status: v.active ? 'running' : 'idle',
        event_count: v.event_count,
        last_event: v.last_event,
      });
    }
  }

  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      <h2 className="text-lg font-bold text-base-100 tracking-tight">System Status</h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {services.map((svc, i) => {
          const isRunning = svc.status === 'running';
          const isIdle = svc.status === 'idle';
          const variant = isRunning ? 'resolved' : isIdle ? 'investigating' : 'critical';
          const dotColor = isRunning ? '#10b981' : isIdle ? '#eab308' : '#ef4444';
          const label = isRunning ? 'Running' : isIdle ? 'Idle' : 'Stopped';
          return (
            <Card key={svc.name + i} className="overflow-hidden">
              <CardContent className="p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="relative inline-flex h-2 w-2 shrink-0">
                      {isRunning && (
                        <span className="absolute inset-0 animate-ping rounded-full opacity-70"
                              style={{ backgroundColor: dotColor }} />
                      )}
                      <span className="relative inline-flex h-2 w-2 rounded-full"
                            style={{ backgroundColor: dotColor, boxShadow: `0 0 6px ${dotColor}aa` }} />
                    </span>
                    <Server className={cn('h-4 w-4 shrink-0', isRunning ? 'text-base-300' : 'text-base-500')} />
                    <span className="truncate text-xs font-semibold text-base-200">{svc.name}</span>
                  </div>
                  <Badge variant={variant}>{label}</Badge>
                </div>
                <div className="space-y-0.5 font-mono text-[10px] text-base-500">
                  {svc.event_count !== undefined && (
                    <div>events: <span className="tabular-nums text-base-300">{svc.event_count}</span></div>
                  )}
                  {svc.incidents !== undefined && (
                    <div>incidents: <span className="tabular-nums text-base-300">{svc.incidents}</span></div>
                  )}
                  {svc.error && <div className="truncate text-red-400" title={svc.error}>err: {svc.error}</div>}
                </div>
              </CardContent>
            </Card>
          );
        })}
        {services.length === 0 && (
          <div className="col-span-full rounded-lg border border-dashed border-base-800 bg-base-950/40 p-6 text-center text-xs text-base-500">
            No status data. Check API connection.
          </div>
        )}
      </div>

      {systemStatus?.uptime_seconds !== undefined && (
        <div className="text-[10px] font-mono text-base-500">
          API uptime: <span className="text-base-300">{systemStatus.uptime_seconds}s</span>
          {' · '}total events: <span className="text-base-300">{systemStatus.total_events ?? 0}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {/* Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ExternalLink className="w-4 h-4 text-red-400" />
              <CardTitle>Red Team Console</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-4">
            <p className="text-xs text-base-400">
              Attack scenarios moved to a standalone console. SecuriSphere is the defender's
              SOC dashboard — attacker controls are isolated on a dedicated page.
            </p>
            <a
              href="/attacker"
              target="_blank"
              rel="noreferrer"
              className="shrink-0 inline-flex items-center gap-1.5 rounded border border-red-500/40 bg-red-500/10 px-3 py-1.5 font-mono text-xs font-semibold uppercase tracking-wider text-red-400 hover:bg-red-500/20"
            >
              Open Attack Console
              <ExternalLink className="h-3 w-3" />
            </a>
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Webhook className="w-4 h-4 text-accent" />
              <CardTitle>Configuration</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div>
              <label className="text-[11px] text-base-400 mb-1 block">WebSocket URL</label>
              <Input defaultValue="ws://localhost:8000" readOnly className="text-xs opacity-60" />
            </div>
            <div>
              <label className="text-[11px] text-base-400 mb-1 block">Refresh Interval</label>
              <Input defaultValue="15000" type="number" className="text-xs" />
            </div>
            <div>
              <label className="text-[11px] text-base-400 mb-1 block">Discord Webhook</label>
              <div className="flex gap-2">
                <Input
                  placeholder="https://discord.com/api/webhooks/..."
                  value={webhook}
                  onChange={e => setWebhook(e.target.value)}
                  className="text-xs flex-1"
                />
                <Button variant="secondary" size="sm">Test</Button>
              </div>
            </div>

            <div className="mt-2">
              <Button variant="secondary" onClick={onRefresh} className="w-full">
                <Server className="w-3.5 h-3.5" /> Refresh System Status
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
