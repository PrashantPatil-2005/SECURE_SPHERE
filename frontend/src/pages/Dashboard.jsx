import { useState, useRef, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Activity, AlertTriangle, Zap, Clock, Radio, ShieldAlert } from 'lucide-react';
import { StatCard } from '@/components/ui/stat-card';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import EventsAreaChart from '@/components/charts/EventsAreaChart';
import ThreatDonutChart from '@/components/charts/ThreatDonutChart';
import TopServicesBar from '@/components/charts/TopServicesBar';
import MitrePanel from '@/components/charts/MitrePanel';
import { cn, severityColor, formatTimestamp, relativeTime, threatLevelColor, getSeverityString, safeString } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

export default function Dashboard({ events = [], incidents = [], metrics = {}, timeline = [], riskScores = {} }) {
  // KPI Calculations safely
  const totalEvents = metrics?.raw_events?.total || events.length;
  const riskEntries = Object.entries(riskScores || {}).filter(([, v]) => v);
  const criticalAlerts = events.filter(e => getSeverityString(e.severity) === 'critical').length;
  const validIncidents = incidents.filter(i => i.mttd_seconds != null);
  const avgMttd = validIncidents.length > 0
    ? Math.round(validIncidents.reduce((sum, i) => sum + (i.mttd_seconds || 0), 0) / validIncidents.length)
    : 0;

  // Topology node data — derive from risk scores
  const topoNodes = useMemo(() => {
    return riskEntries.slice(0, 8).map(([ip, data], idx) => {
      const score = data?.current_score || 0;
      const level = safeString(data?.threat_level || 'normal').toLowerCase();
      return { ip, score, level, idx };
    });
  }, [riskEntries]);

  // Auto-scroll feed
  const [autoScroll, setAutoScroll] = useState(true);
  const feedRef = useRef(null);
  useEffect(() => {
    if (autoScroll && feedRef.current) feedRef.current.scrollTop = 0;
  }, [events, autoScroll]);

  return (
    <motion.div {...anim} className="flex flex-col gap-6">
      {/* KPI Row (Row 1) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Events"
          value={totalEvents.toLocaleString()}
          icon={Activity}
          color="accent"
          sub={events.length > 0 ? <><span className="text-green-400 font-semibold">+{events.length}</span> in window</> : 'Awaiting data'}
        />
        <StatCard
          label="Active Incidents"
          value={incidents.length}
          icon={AlertTriangle}
          color={incidents.length > 0 ? 'red' : 'muted'}
          glow={incidents.length > 0}
          sub={`${incidents.filter(i => getSeverityString(i?.severity) === 'critical').length} critical, ${incidents.filter(i => getSeverityString(i?.severity) === 'high').length} high`}
        />
        <StatCard
          label="Critical Alerts"
          value={criticalAlerts}
          icon={Zap}
          color={criticalAlerts > 0 ? 'orange' : 'muted'}
          pulse={criticalAlerts > 0}
          sub={`${events.filter(e => getSeverityString(e.severity) === 'high').length} high, ${events.filter(e => getSeverityString(e.severity) === 'medium').length} medium`}
        />
        <StatCard
          label="Avg MTTD"
          value={avgMttd > 0 ? `${avgMttd}s` : '\u2014'}
          icon={Clock}
          color="cyan"
          sub="mean time to detect"
        />
      </div>

      {/* Primary Analytics (Row 2) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Events Over Time</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {timeline.length > 0 ? (
              <EventsAreaChart data={timeline} />
            ) : (
              <div className="h-[200px] flex items-center justify-center text-xs text-base-500">No timeline data</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Threat Distribution</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center pt-0">
            <ThreatDonutChart events={events} />
          </CardContent>
        </Card>
      </div>

      {/* Network Risk & Topology Summary (Row 3) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Heatmap */}
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-white/[0.05] mb-4">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-orange-500" />
              <CardTitle>Risk Heatmap</CardTitle>
            </div>
            <span className="text-xs text-base-500 font-mono">{riskEntries.length} entities</span>
          </CardHeader>
          <CardContent className="max-h-[300px] overflow-y-auto px-4 pb-4">
            {riskEntries.length > 0 ? (
              <div className="flex flex-col gap-3">
                {riskEntries.slice(0, 6).map(([ip, data]) => {
                  const score = data?.current_score || 0;
                  const level = safeString(data?.threat_level || 'normal').toLowerCase();
                  const color = threatLevelColor(level);
                  const pct = Math.min(100, (score / 200) * 100);
                  return (
                    <div key={ip} className="bg-base-900 border border-white/[0.05] rounded-lg p-3 relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: color }} />
                      <div className="flex justify-between items-center mb-2 pl-2">
                        <span className="font-mono text-sm text-base-100 font-semibold">{ip}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold" style={{ color }}>{score}</span>
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider" style={{ backgroundColor: `${color}15`, color }}>
                            {level}
                          </span>
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-black/40 rounded-full overflow-hidden pl-2">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundImage: `linear-gradient(90deg, ${color}, ${color}88)` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-8 text-center text-base-500 text-sm">No risk data available</div>
            )}
          </CardContent>
        </Card>

         <Card>
          <CardHeader>
            <CardTitle>Top Attacked Services</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <TopServicesBar events={events} />
          </CardContent>
        </Card>
      </div>

      {/* Live Feed + Incidents (Row 4) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Live Event Feed */}
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-white/[0.05]">
            <div className="flex items-center gap-2">
              <CardTitle>Live Event Feed</CardTitle>
              <div className="w-[7px] h-[7px] rounded-full bg-green-500 shadow-[0_0_6px_rgba(95,140,110,0.6)] animate-pulse-glow" />
            </div>
            <label className="flex items-center gap-1.5 text-[10px] text-base-500 cursor-pointer">
              <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} className="accent-accent w-3 h-3" />
              Auto
            </label>
          </CardHeader>
          <div ref={feedRef} className="max-h-[340px] overflow-y-auto px-1 py-2">
            {events.length > 0 ? events.slice(0, 25).map((ev, i) => (
              <div
                key={ev.event_id || i}
                className={cn(
                  'flex items-center gap-3 px-4 py-2 hover:bg-white/[0.02] transition-colors rounded-xl mx-2 mb-1 border border-transparent hover:border-white/[0.05]',
                  i === 0 && 'animate-flash-row'
                )}
              >
                <div className="w-2 h-2 rounded-full shrink-0" style={{ background: severityColor(ev.severity), boxShadow: `0 0 6px ${severityColor(ev.severity)}` }} />
                <span className="text-[11px] font-mono text-base-500 w-14 shrink-0">{formatTimestamp(ev.timestamp)}</span>
                <span className="text-xs font-medium text-base-200 flex-1 truncate">{safeString(ev.event_type)}</span>
                <span className="text-[11px] font-mono text-accent shrink-0">{ev.source_entity?.ip || ev.source_entity?.service || '\u2014'}</span>
                <Badge variant={safeString(ev.source_layer || 'default').toLowerCase()} className="text-[9px]">
                  {safeString(ev.source_layer || 'N/A').toUpperCase()}
                </Badge>
              </div>
            )) : (
              <div className="flex flex-col items-center justify-center py-12 text-base-500 text-xs gap-2">
                <Radio className="w-6 h-6 opacity-30" />
                No events yet
              </div>
            )}
          </div>
        </Card>

        {/* Active Incidents */}
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-white/[0.05]">
            <div className="flex items-center gap-2">
              <CardTitle>Active Incidents</CardTitle>
            </div>
            {incidents.length > 0 && (
              <span className="text-[10px] font-bold font-mono px-1.5 rounded-full bg-accent/10 text-accent">{incidents.length}</span>
            )}
          </CardHeader>
          <div className="max-h-[340px] overflow-y-auto px-1 py-2">
            {incidents.length > 0 ? incidents.slice(0, 8).map(inc => (
              <div key={inc.incident_id} className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors rounded-xl mx-2 mb-1 border border-white/[0.02] bg-base-900/40">
                <div className="w-[3px] h-9 rounded-full mt-0.5 shrink-0" style={{ background: severityColor(inc.severity) }} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-base-100 truncate">{safeString(inc.title)}</div>
                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                    {inc.mitre_techniques?.map(t => (
                      <span key={safeString(t)} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-accent/[0.08] text-accent border border-accent/10">{safeString(t)}</span>
                    ))}
                    {inc.kill_chain_steps && (
                      <span className="text-[9px] font-mono text-base-500">
                        {Array.isArray(inc.kill_chain_steps) ? inc.kill_chain_steps.length : inc.kill_chain_steps} steps
                      </span>
                    )}
                    {inc.mttd_seconds != null && (
                      <span className="text-[9px] font-mono font-semibold text-green-400 px-1.5 py-0.5 rounded bg-green-500/10">MTTD: {Math.round(inc.mttd_seconds)}s</span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <Badge variant={getSeverityString(inc.severity)}>{getSeverityString(inc.severity)}</Badge>
                  <span className="text-[10px] font-mono text-base-500">{relativeTime(inc.timestamp)}</span>
                </div>
              </div>
            )) : (
              <div className="flex flex-col items-center justify-center py-12 text-base-500 text-xs gap-2">
                <AlertTriangle className="w-6 h-6 opacity-30" />
                No incidents detected
              </div>
            )}
          </div>
        </Card>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        <MitrePanel />
      </div>

    </motion.div>
  );
}
