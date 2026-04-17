import { useState } from 'react';
import { motion } from 'framer-motion';
import { Server, Play, Loader2, Terminal, Webhook } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

const FALLBACK_CONTAINERS = [
  'api-gateway', 'frontend', 'database', 'topology-collector'
];

export default function System({ systemStatus = {}, onRefresh }) {
  const [simLog, setSimLog] = useState([]);
  const [running, setRunning] = useState(null);
  const [webhook, setWebhook] = useState('');

  const runScenario = async (scenario) => {
    setRunning(scenario);
    setSimLog(prev => [...prev, `[${new Date().toLocaleTimeString()}] Starting Scenario ${scenario.toUpperCase()}...`]);
    try {
      const res = await api.simulateAttack(scenario);
      setSimLog(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${res.message || 'Scenario launched'}`]);
    } catch (err) {
      setSimLog(prev => [...prev, `[${new Date().toLocaleTimeString()}] Error: ${err.message}`]);
    } finally {
      setRunning(null);
    }
  };

  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      <h2 className="text-lg font-bold text-base-100 tracking-tight">System Status</h2>

      {/* Container health grid */}
      <div className="grid grid-cols-4 gap-3">
        {(() => {
          const list = [];
          if(systemStatus?.redis) list.push({ name: 'redis-cache', ...systemStatus.redis, status: systemStatus.redis.connected ? 'running' : 'stopped' });
          if(systemStatus?.correlation_engine) list.push({ name: 'correlation-engine', ...systemStatus.correlation_engine, status: systemStatus.correlation_engine.active ? 'running' : 'stopped' });
          if(systemStatus?.monitors) {
            for(const [k, v] of Object.entries(systemStatus.monitors)) {
              list.push({ name: `${k}-monitor`, ...v, status: v.active ? 'running' : 'stopped' });
            }
          }
          for(const name of FALLBACK_CONTAINERS) {
            list.push({ name, status: 'healthy' });
          }
          return list.map((svc, i) => {
            const isUp = svc.status === 'running' || svc.status === 'active' || svc.status === 'healthy';
            return (
              <Card key={svc.name + i} className="overflow-hidden">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Server className={cn('w-4 h-4', isUp ? 'text-green-400' : 'text-red-400')} />
                      <span className="text-xs font-semibold text-base-200 truncate">{svc.name}</span>
                    </div>
                    <Badge variant={isUp ? 'low' : 'critical'}>
                      {isUp ? 'Running' : svc.status || 'Stopped'}
                    </Badge>
                  </div>
                  {(svc.uptime || systemStatus?.uptime_seconds) && (
                    <span className="text-[10px] font-mono text-base-500">Up: {svc.uptime || `${systemStatus.uptime_seconds}s`}</span>
                  )}
                  {svc.event_count !== undefined && (
                    <span className="text-[10px] font-mono text-base-500 ml-2">events: {svc.event_count}</span>
                  )}
                </CardContent>
              </Card>
            );
          });
        })()}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Attack Simulator */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-accent" />
              <CardTitle>Attack Simulator</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex gap-2">
              {['a', 'b', 'c'].map(scenario => (
                <Button
                  key={scenario}
                  variant="primary"
                  size="md"
                  onClick={() => runScenario(scenario)}
                  disabled={running !== null}
                  className="flex-1"
                >
                  {running === scenario ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  Scenario {scenario.toUpperCase()}
                </Button>
              ))}
            </div>

            {/* Sim log */}
            <div className="h-40 rounded-lg bg-base-950 border border-white/[0.05] p-3 overflow-y-auto font-mono text-[11px] text-base-400 leading-relaxed">
              {simLog.length > 0 ? simLog.map((line, i) => (
                <div key={i} className="py-0.5">{line}</div>
              )) : (
                <div className="text-base-600">Click a scenario to start attack simulation...</div>
              )}
            </div>
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
