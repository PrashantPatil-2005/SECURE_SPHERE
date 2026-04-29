import { useState, useMemo, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle, Play, ChevronDown, ChevronRight, Clock, Target,
  Activity, StickyNote, Loader2, Network, FileText,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/input';
import KillChainTimeline from '@/components/KillChainTimeline';
import IncidentActions from '@/components/IncidentActions';
import MttdPanel from '@/components/charts/MttdPanel';
import {
  cn, severityColor, layerColor, formatTimestampFull, relativeTime,
  getSeverityString, safeString,
} from '@/lib/utils';
import { api } from '@/lib/api';
import { useAppStore } from '@/stores/useAppStore';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

const DEFAULT_STATUS = 'open';

// Normalize server/legacy status values into the triage filter buckets.
function normaliseStatus(s) {
  const v = safeString(s).toLowerCase();
  if (!v || v === 'active') return 'open';
  if (v === 'investigating') return 'acknowledged';
  return v;
}

const STATUS_FILTERS = [
  { key: 'all',          label: 'All' },
  { key: 'open',         label: 'Open' },
  { key: 'acknowledged', label: 'Acknowledged' },
  { key: 'resolved',     label: 'Resolved' },
];

const STATUS_BADGE_CLASS = {
  open:         'bg-base-800/50 text-base-300 border-base-700',
  acknowledged: 'bg-yellow-500/10 text-yellow-300 border-yellow-500/25',
  resolved:     'bg-emerald-500/10 text-emerald-300 border-emerald-500/25',
  escalated:    'bg-red-500/15 text-red-300 border-red-500/30',
  suppressed:   'bg-base-800/50 text-base-400 border-base-700',
};

function StatusBadge({ status }) {
  const norm = normaliseStatus(status);
  const cls = STATUS_BADGE_CLASS[norm] || STATUS_BADGE_CLASS.open;
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border',
      cls,
    )}>
      {norm}
    </span>
  );
}

// ---------------------------------------------------------------------------
// IncidentCard — one row per incident, with expandable drill-down.
// ---------------------------------------------------------------------------
function IncidentCard({ inc, onReplay, replaying, onStatusChange }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [report, setReport] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  const status = safeString(inc.status) || DEFAULT_STATUS;
  const sev = getSeverityString(inc.severity);
  const mttd = inc.mttd_seconds;
  const duration = inc.duration_seconds;

  const loadDetail = useCallback(async () => {
    if (detail || loadingDetail) return;
    setLoadingDetail(true);
    setDetailError('');
    try {
      const res = await api.getKillChain(inc.incident_id);
      setDetail(res?.kill_chain || res);
    } catch (e) {
      setDetailError('Failed to fetch kill-chain detail.');
    } finally {
      setLoadingDetail(false);
    }
  }, [inc.incident_id, detail, loadingDetail]);

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    if (next) {
      loadDetail();
      fetchExistingReport();
    }
  };

  const fetchExistingReport = async () => {
    try {
      const res = await fetch(`/api/ai/reports/${inc.incident_id}`);
      if (res.ok) {
        const data = await res.json();
        if (data.reports && data.reports.length > 0) {
          setReport(data.reports[data.reports.length - 1].content);
        }
      }
    } catch (e) {
      console.error('Failed to fetch existing reports', e);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const res = await fetch(`/api/ai/report/${inc.incident_id}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setReport(data.report);
        }
      }
    } catch (e) {
      console.error('Failed to generate report', e);
    } finally {
      setGeneratingReport(false);
    }
  };

  // Prefer rich step array from drill-down, then inline steps/service_path.
  const richSteps = detail?.steps || (Array.isArray(inc.steps) ? inc.steps : null);
  const servicePath = inc.service_path || detail?.service_path || [];
  const firstService = inc.first_service || detail?.first_service;
  const lastService = inc.last_service || detail?.last_service;
  const firstEventAt = inc.first_event_at || detail?.first_event_at;
  const detectedAt = inc.detected_at || detail?.detected_at;
  const analystNote = inc.analyst_note ?? detail?.analyst_note;

  return (
    <Card glow={sev === 'critical'} className="overflow-hidden">
      {/* ------ Summary row ------ */}
      <div className="flex items-start gap-4 p-4">
        <div className="w-1 rounded-full self-stretch shrink-0" style={{ background: severityColor(inc.severity) }} />

        <div className="flex-1 min-w-0">
          {/* Title row */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="text-sm font-semibold text-base-100 truncate">
              {safeString(inc.scenario_label || inc.title || inc.incident_type)}
            </h3>
            <Badge variant={sev}>{sev}</Badge>
            <StatusBadge status={status} />
            {mttd != null && (
              <span className="text-[10px] font-mono font-semibold text-severity-low px-2 py-0.5 rounded bg-severity-low/10 border border-severity-low/20">
                MTTD: {Math.round(mttd)}s
              </span>
            )}
            {duration != null && (
              <span className="text-[10px] font-mono text-base-500 px-2 py-0.5 rounded bg-base-950/40 border border-base-800">
                duration: {Math.round(duration)}s
              </span>
            )}
            <span className="text-[10px] font-mono text-base-500 ml-auto shrink-0">
              {relativeTime(inc.timestamp || detectedAt)}
            </span>
          </div>

          {/* Narrative */}
          {inc.narrative && (
            <p className="text-[11px] text-base-400 mt-1 mb-3 leading-relaxed border-l-2 border-base-800 pl-2 italic">
              {inc.narrative}
            </p>
          )}

          {/* Meta row */}
          <div className="flex items-center gap-3 mb-3 text-[11px] text-base-400 flex-wrap">
            {inc.source_ip && (
              <span className="font-mono text-accent inline-flex items-center gap-1">
                <Target className="w-3 h-3" /> {safeString(inc.source_ip)}
              </span>
            )}
            {(firstService || lastService) && (
              <span className="font-mono text-base-400 inline-flex items-center gap-1">
                <Network className="w-3 h-3 text-base-500" />
                {safeString(firstService || '\u2014')} → {safeString(lastService || '\u2014')}
              </span>
            )}
            {inc.event_count != null && (
              <span className="inline-flex items-center gap-1">
                <Activity className="w-3 h-3 text-base-500" /> {inc.event_count} events
              </span>
            )}
            {(richSteps?.length || servicePath.length || inc.kill_chain_steps) && (
              <span>
                {richSteps?.length || servicePath.length || (Array.isArray(inc.kill_chain_steps) ? inc.kill_chain_steps.length : inc.kill_chain_steps)} kill-chain steps
              </span>
            )}
            {inc.mitre_techniques?.map(t => (
              <span key={safeString(t)} className="font-mono px-1.5 py-0.5 rounded bg-accent/[0.06] text-accent border border-accent/10">
                {safeString(t)}
              </span>
            ))}
            {inc.layers_involved?.map(l => {
              const hex = layerColor(safeString(l));
              return (
                <span
                  key={safeString(l)}
                  className="font-mono px-1.5 py-0.5 rounded border capitalize"
                  style={{ color: hex, borderColor: `${hex}30`, backgroundColor: `${hex}12` }}
                >
                  {safeString(l)}
                </span>
              );
            })}
          </div>

          {/* Timeline preview */}
          {(richSteps?.length > 0 || servicePath.length > 0 || (inc.kill_chain_steps && Number(inc.kill_chain_steps) > 0)) && (
            <KillChainTimeline
              steps={richSteps || inc.kill_chain_steps || 0}
              servicePath={servicePath}
              mitreTechniques={inc.mitre_techniques || []}
              compact={!expanded}
            />
          )}

          {/* Analyst note preview */}
          {analystNote && !expanded && (
            <div className="mt-2 flex items-start gap-1.5 text-[11px] text-base-400 border-l-2 border-accent/30 pl-2">
              <StickyNote className="w-3 h-3 mt-0.5 text-accent shrink-0" />
              <span className="italic truncate">{analystNote}</span>
            </div>
          )}
        </div>

        {/* Right column actions */}
        <div className="flex flex-col items-end gap-2 shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onReplay(inc)}
            disabled={replaying}
            title="Replay this scenario"
          >
            <Play className="w-3 h-3" />
            {replaying ? 'Playing…' : 'Replay'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggle}
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {expanded ? 'Hide' : 'Details'}
          </Button>
        </div>
      </div>

      {/* ------ Expanded drill-down ------ */}
      {expanded && (
        <div className="border-t border-base-800 bg-base-900/40 p-4 flex flex-col gap-4">
          {/* Timestamps */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
            <DetailCell label="First event" icon={Clock}
              value={firstEventAt ? formatTimestampFull(firstEventAt) : '\u2014'} />
            <DetailCell label="Detected at" icon={Clock}
              value={detectedAt ? formatTimestampFull(detectedAt) : '\u2014'}
              tone="text-severity-low" />
            <DetailCell label="MTTD"
              value={mttd != null ? `${Math.round(mttd * 100) / 100}s` : '\u2014'} />
          </div>

          {/* Triage actions */}
          <div>
            <div className="text-[10px] uppercase tracking-wider font-semibold text-base-500 mb-1.5">Triage</div>
            <IncidentActions
              incidentId={inc.incident_id}
              currentStatus={status}
              onChange={(newStatus, note) => onStatusChange(inc.incident_id, newStatus, note)}
            />
          </div>

          {/* Analyst note full */}
          {analystNote && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-accent/[0.04] border border-accent/15">
              <StickyNote className="w-3.5 h-3.5 text-accent mt-0.5 shrink-0" />
              <div className="text-[11px] text-base-300 leading-relaxed">
                <div className="text-[9px] uppercase tracking-wider text-base-500 mb-0.5">Analyst note</div>
                {analystNote}
              </div>
            </div>
          )}

          {/* AI Report Section */}
          <div className="border-t border-base-800 pt-4">
            <div className="flex justify-between items-center mb-2">
              <div className="text-[10px] uppercase tracking-wider font-semibold text-base-500">AI Incident Report</div>
              <Button size="sm" variant="outline" onClick={handleGenerateReport} disabled={generatingReport}>
                {generatingReport ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <FileText className="w-3 h-3 mr-1" />}
                {generatingReport ? 'Generating...' : report ? 'Regenerate Report' : 'Generate Report'}
              </Button>
            </div>
            {report && (
              <div className="mt-2 p-3 bg-base-950 rounded-md border border-base-800 text-[11px] font-mono text-base-300 whitespace-pre-wrap overflow-x-auto">
                {report}
              </div>
            )}
          </div>

          {/* Full step table */}
          {loadingDetail ? (
            <div className="py-4 flex items-center justify-center gap-2 text-xs text-base-500">
              <Loader2 className="w-4 h-4 animate-spin text-accent" /> Loading kill-chain…
            </div>
          ) : detailError ? (
            <div className="text-xs text-base-400">{detailError}</div>
          ) : richSteps?.length > 0 ? (
            <StepTable steps={richSteps} />
          ) : (
            <div className="text-[11px] text-base-500 italic">No detailed step data available.</div>
          )}

          {detail?.source && (
            <span className="self-end text-[9px] font-mono text-base-500 uppercase tracking-wider">
              source: {detail.source}
            </span>
          )}
        </div>
      )}
    </Card>
  );
}

function DetailCell({ label, value, icon: Icon, tone }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[9px] uppercase tracking-wider font-semibold text-base-500 flex items-center gap-1">
        {Icon && <Icon className="w-2.5 h-2.5" />}
        {label}
      </span>
      <span className={cn('font-mono text-base-200 text-xs', tone)}>{value}</span>
    </div>
  );
}

function StepTable({ steps }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="text-[9px] uppercase tracking-wider text-base-500 border-b border-base-800">
            <th className="text-left font-semibold py-1.5 pl-1 w-8">#</th>
            <th className="text-left font-semibold py-1.5 px-2">Service</th>
            <th className="text-left font-semibold py-1.5 px-2">Layer</th>
            <th className="text-left font-semibold py-1.5 px-2">Event</th>
            <th className="text-left font-semibold py-1.5 px-2">MITRE</th>
            <th className="text-left font-semibold py-1.5 px-2">Severity</th>
            <th className="text-right font-semibold py-1.5 pr-1">Time</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((s, i) => {
            const service = s.service_name || s.service || s.source_service_name || '\u2014';
            const layer = s.layer || s.source_layer || null;
            const layerHex = layer ? layerColor(layer) : null;
            const event = s.event_type || s.description || '\u2014';
            const mitre = s.mitre || s.technique || (Array.isArray(s.mitre_techniques) ? s.mitre_techniques.join(', ') : '\u2014');
            const severity = s.severity ? getSeverityString(s.severity) : null;
            const sevHex = severity ? severityColor(severity) : null;
            const ts = s.timestamp || s.ts;
            return (
              <tr key={i} className="border-b border-base-800 hover:bg-base-950/35">
                <td className="py-1.5 pl-1 font-mono text-base-500">{i + 1}</td>
                <td className="py-1.5 px-2 font-semibold text-base-100">{safeString(service)}</td>
                <td className="py-1.5 px-2">
                  {layer ? (
                    <span
                      className="font-mono text-[9px] px-1 py-0.5 rounded border uppercase"
                      style={{ color: layerHex, borderColor: `${layerHex}30`, backgroundColor: `${layerHex}12` }}
                    >
                      {safeString(layer)}
                    </span>
                  ) : <span className="text-base-500">{'\u2014'}</span>}
                </td>
                <td className="py-1.5 px-2 text-base-300">{safeString(event)}</td>
                <td className="py-1.5 px-2 font-mono text-accent">{safeString(mitre)}</td>
                <td className="py-1.5 px-2">
                  {severity ? (
                    <span className="inline-flex items-center gap-1 font-mono" style={{ color: sevHex }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sevHex }} />
                      {severity}
                    </span>
                  ) : <span className="text-base-500">{'\u2014'}</span>}
                </td>
                <td className="py-1.5 pr-1 text-right font-mono text-base-500">
                  {ts ? formatTimestampFull(ts) : '\u2014'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function Incidents({ incidents, onReplayRequest }) {
  const kcMode = useAppStore((s) => s.kc);
  const [statusFilter, setStatusFilter] = useState('all');
  const [sevFilter, setSevFilter] = useState('all');
  const [replayingId, setReplayingId] = useState(null);
  const [richKillChains, setRichKillChains] = useState({});
  const [statusOverrides, setStatusOverrides] = useState({});

  // Poll list of kill chains (for scenario_label/narrative/status/analyst_note/steps enrichment)
  useEffect(() => {
    let cancelled = false;
    const fetchKC = async () => {
      try {
        const res = await api.getKillChains(50);
        if (cancelled) return;
        const map = {};
        for (const kc of (res.kill_chains || [])) {
          map[kc.incident_id] = kc;
        }
        setRichKillChains(map);
      } catch (e) {
        console.error('Failed fetching rich kill chains:', e);
      }
    };
    fetchKC();
    const id = setInterval(fetchKC, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // Merge live incidents with enriched kill-chain rows and local status overrides.
  const augmentedIncidents = useMemo(() => {
    return (incidents || []).map(inc => {
      const kc = richKillChains[inc.incident_id];
      const override = statusOverrides[inc.incident_id];
      const merged = kc ? { ...inc, ...kc } : inc;
      return override
        ? { ...merged, status: override.status, analyst_note: override.note || merged.analyst_note }
        : merged;
    });
  }, [incidents, richKillChains, statusOverrides]);

  const filtered = useMemo(() => {
    return augmentedIncidents.filter(inc => {
      const st = normaliseStatus(inc.status);
      if (statusFilter !== 'all' && st !== statusFilter) return false;
      if (sevFilter !== 'all' && getSeverityString(inc.severity) !== sevFilter) return false;
      return true;
    });
  }, [augmentedIncidents, statusFilter, sevFilter]);

  const handleReplay = (inc) => {
    setReplayingId(inc.incident_id);
    if (onReplayRequest) onReplayRequest(inc.incident_id);
    setTimeout(() => setReplayingId(null), 3000);
  };

  const handleStatusChange = (incidentId, status, note) => {
    setStatusOverrides(prev => ({ ...prev, [incidentId]: { status, note } }));
  };

  return (
    <motion.div {...anim} data-kc-view={kcMode} className="flex flex-col gap-4">
      {/* MTTD evaluation panel */}
      <MttdPanel />

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <h2 className="text-lg font-bold text-base-100 tracking-tight">Kill Chains / Incidents</h2>
        <span className="text-xs font-mono text-base-500">{filtered.length} / {augmentedIncidents.length} incidents</span>
        <div className="ml-auto flex items-center gap-2">
          <Select value={sevFilter} onChange={e => setSevFilter(e.target.value)}>
            <option value="all">All Severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </Select>
        </div>
      </div>

      {/* Status filter button row */}
      <div className="inline-flex items-center gap-1 p-1 rounded-lg border border-base-800 bg-base-900/40 self-start">
        {STATUS_FILTERS.map(f => {
          const active = statusFilter === f.key;
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => setStatusFilter(f.key)}
              className={cn(
                'h-7 px-3 rounded-md text-[11px] font-semibold uppercase tracking-wider transition-colors',
                active
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'text-base-400 hover:text-base-200 hover:bg-base-800/40 border border-transparent',
              )}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Incident cards */}
      {filtered.length > 0 ? (
        <div className="flex flex-col gap-3">
          {filtered.map(inc => (
            <IncidentCard
              key={inc.incident_id}
              inc={inc}
              onReplay={handleReplay}
              replaying={replayingId === inc.incident_id}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-16 text-center">
            <AlertTriangle className="w-8 h-8 mx-auto mb-3 text-base-500 opacity-30" />
            <p className="text-sm text-base-500">No incidents match filters</p>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
