import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, Target, Clock, ChevronRight, Network, Shield,
  AlertTriangle, RefreshCw, Loader2, Users, X,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/button';
import EmptyState from '@/components/ui/EmptyState';
import {
  cn, severityColor, formatTimestampFull, relativeTime, getSeverityString,
} from '@/lib/utils';
import { api } from '@/lib/api';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

const STATUS_FILTERS = [
  { key: 'all',    label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'closed', label: 'Closed' },
];

const SEVERITY_FILTERS = [
  { key: '',         label: 'Any severity' },
  { key: 'critical', label: 'Critical' },
  { key: 'high',     label: 'High' },
  { key: 'medium',   label: 'Medium' },
  { key: 'low',      label: 'Low' },
];

function StatPill({ label, value, tone = 'base' }) {
  const toneClass = {
    base:     'bg-base-800/50 text-base-200 border-base-700',
    critical: 'bg-red-500/10 text-red-300 border-red-500/30',
    high:     'bg-orange-500/10 text-orange-300 border-orange-500/30',
    accent:   'bg-accent-muted text-accent border-accent/30',
  }[tone];
  return (
    <div className={cn('rounded-lg border px-3 py-2', toneClass)}>
      <div className="text-2xs uppercase tracking-wider opacity-70">{label}</div>
      <div className="font-mono tabular-nums text-lg font-semibold">{value}</div>
    </div>
  );
}

function SeverityChip({ sev }) {
  const norm = getSeverityString(sev);
  return (
    <Badge variant={norm}>
      {norm.toUpperCase()}
    </Badge>
  );
}

function StagesTrack({ stages = [] }) {
  const ALL = [
    'reconnaissance', 'weaponization', 'delivery',
    'exploitation', 'installation', 'command_and_control',
    'actions_on_objectives',
  ];
  const set = new Set(stages);
  return (
    <div className="flex flex-wrap items-center gap-1">
      {ALL.map((s, i) => (
        <span key={s} className="flex items-center">
          <span
            className={cn(
              'rounded px-1.5 py-0.5 text-2xs uppercase tracking-wider border font-mono',
              set.has(s)
                ? 'bg-accent-muted text-accent border-accent/40'
                : 'bg-base-900/40 text-base-500 border-base-800',
            )}
            title={s.replace(/_/g, ' ')}
          >
            {s.split('_')[0].slice(0, 4)}
          </span>
          {i < ALL.length - 1 && (
            <ChevronRight className="w-3 h-3 text-base-700 mx-0.5" />
          )}
        </span>
      ))}
    </div>
  );
}

function ServicePath({ path = [] }) {
  if (!path.length) return <span className="text-base-500 text-xs">—</span>;
  return (
    <div className="flex flex-wrap items-center gap-1 font-mono text-xs">
      {path.map((svc, i) => (
        <span key={i} className="flex items-center">
          <span className="px-1.5 py-0.5 rounded bg-base-800/60 border border-base-700 text-base-200">
            {svc}
          </span>
          {i < path.length - 1 && (
            <ChevronRight className="w-3 h-3 text-base-600 mx-0.5" />
          )}
        </span>
      ))}
    </div>
  );
}

function CampaignCard({ campaign, onSelect }) {
  const sev = getSeverityString(campaign.severity);
  const borderTint = {
    critical: 'border-red-500/30',
    high:     'border-orange-500/30',
    medium:   'border-amber-500/25',
    low:      'border-base-700',
  }[sev] || 'border-base-700';
  const isClosed = campaign.status === 'closed';

  return (
    <motion.button
      {...anim}
      onClick={() => onSelect(campaign)}
      className={cn(
        'w-full text-left rounded-[10px] border bg-base-900/60 p-4',
        'hover:bg-base-900/80 hover:border-accent/40 transition-colors',
        borderTint,
        isClosed && 'opacity-70',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityChip sev={sev} />
            {isClosed && (
              <Badge variant="resolved">CLOSED</Badge>
            )}
            <span className="font-mono text-xs text-base-400 tabular-nums">
              <span className="font-mono">{campaign.actor_id}</span>
              {campaign.actor_type && (
                <Badge variant="info" className="ml-2 text-2xs">
                  {campaign.actor_type}
                </Badge>
              )}
            </span>
          </div>
          <div className="mt-2 flex items-center gap-2 text-base-100 font-semibold">
            <Target className="w-4 h-4 text-accent" />
            {campaign.incident_count} correlated incident{campaign.incident_count === 1 ? '' : 's'}
            <span className="text-base-500 font-normal">
              · {(campaign.mitre_techniques || []).length} MITRE techniques
            </span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-2xs uppercase tracking-wider text-base-500">Last seen</div>
          <div className="font-mono text-xs text-base-300 tabular-nums">
            {relativeTime(campaign.last_event_at)}
          </div>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        <StagesTrack stages={campaign.stages_seen} />
        <ServicePath path={campaign.service_path} />
      </div>

      <div className="mt-3 flex items-center justify-between text-2xs text-base-500 font-mono tabular-nums">
        <span>
          first seen <span className="text-base-300">{formatTimestampFull(campaign.first_event_at)}</span>
        </span>
        <span className="text-base-400">
          confidence {Number(campaign.max_confidence || 0).toFixed(2)}
        </span>
      </div>
    </motion.button>
  );
}

function CampaignDrawer({ campaign, onClose }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!campaign) return;
    setDetail(null);
    setErr(null);
    setLoading(true);
    api.getCampaign(campaign.campaign_id)
      .then((r) => setDetail(r?.data))
      .catch((e) => setErr(e.message || 'Failed to load campaign'))
      .finally(() => setLoading(false));
  }, [campaign]);

  if (!campaign) return null;
  const sev = getSeverityString(campaign.severity);

  return (
    <div className="fixed inset-0 z-50 flex">
      <div
        className="flex-1 bg-base-950/70 backdrop-blur-sm"
        onClick={onClose}
        role="presentation"
      />
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-2xl bg-base-900 border-l border-base-800 overflow-y-auto"
      >
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-base-800 bg-base-900/95 backdrop-blur">
          <div className="flex items-center gap-2 min-w-0">
            <SeverityChip sev={sev} />
            <span className="font-mono text-sm text-base-200 truncate">
              <span className="font-mono">{campaign.actor_id}</span>
              {campaign.actor_type && (
                <Badge variant="info" className="ml-2 text-2xs">
                  {campaign.actor_type}
                </Badge>
              )}
            </span>
          </div>
          <Button variant="icon" size="icon" onClick={onClose} aria-label="Close">
            <X className="w-4 h-4" />
          </Button>
        </div>

        {loading && (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-5 h-5 animate-spin text-accent" />
          </div>
        )}

        {err && (
          <div className="p-6">
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm">
              {err}
            </div>
          </div>
        )}

        {detail && !loading && (
          <div className="p-4 space-y-5">
            <div className="grid grid-cols-2 gap-3">
              <StatPill label="Incidents"       value={detail.campaign.incident_count} tone="accent" />
              <StatPill label="MITRE techniques" value={(detail.campaign.mitre_techniques || []).length} />
              <StatPill label="Services hit"    value={(detail.campaign.service_path || []).length} />
              <StatPill label="Stages reached"  value={(detail.campaign.stages_seen || []).length} tone={sev} />
            </div>

            <Card>
              <div className="p-4">
                <div className="text-2xs uppercase tracking-wider text-base-500 mb-2">
                  Kill chain stages
                </div>
                <StagesTrack stages={detail.campaign.stages_seen} />
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="text-2xs uppercase tracking-wider text-base-500 mb-2">
                  Service attack path
                </div>
                <ServicePath path={detail.campaign.service_path} />
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="text-2xs uppercase tracking-wider text-base-500 mb-2">
                  MITRE techniques ({(detail.campaign.mitre_techniques || []).length})
                </div>
                <div className="flex flex-wrap gap-1">
                  {(detail.campaign.mitre_techniques || []).map((t) => (
                    <a
                      key={t}
                      href={`https://attack.mitre.org/techniques/${String(t).replace('.', '/')}`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-1.5 py-0.5 rounded text-xs font-mono bg-base-800/60 border border-base-700 text-base-200 hover:border-accent/40 hover:text-accent"
                    >
                      {t}
                    </a>
                  ))}
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="text-2xs uppercase tracking-wider text-base-500 mb-3">
                  Constituent incidents ({detail.incidents.length})
                </div>
                <div className="space-y-2">
                  {detail.incidents.map((inc) => (
                    <div
                      key={inc.incident_id}
                      className="rounded-lg border border-base-800 bg-base-950/40 p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <SeverityChip sev={inc.severity} />
                          <span className="font-mono text-xs text-base-300 truncate">
                            {inc.incident_type}
                          </span>
                        </div>
                        {inc.technique_id && (
                          <span className="font-mono text-2xs text-accent">
                            {inc.technique_id}
                          </span>
                        )}
                      </div>
                      {inc.title && (
                        <div className="mt-1 text-sm text-base-200">{inc.title}</div>
                      )}
                      {inc.description && (
                        <div className="mt-1 text-xs text-base-500 line-clamp-2">
                          {inc.description}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-4">
                <div className="text-2xs uppercase tracking-wider text-base-500 mb-3">
                  Campaign metadata
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono text-base-300">
                  <div><span className="text-base-500">campaign_id:</span><br/>{detail.campaign.campaign_id}</div>
                  <div><span className="text-base-500">status:</span> {detail.campaign.status}</div>
                  <div><span className="text-base-500">first_event_at:</span><br/>{formatTimestampFull(detail.campaign.first_event_at)}</div>
                  <div><span className="text-base-500">last_event_at:</span><br/>{formatTimestampFull(detail.campaign.last_event_at)}</div>
                  {detail.campaign.closed_reason && (
                    <div className="col-span-2">
                      <span className="text-base-500">closed_reason:</span> {detail.campaign.closed_reason}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [stats, setStats] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [list, st] = await Promise.all([
        api.getCampaigns({ status: statusFilter, severity: severityFilter, limit: 100 }),
        api.getCampaignStats(),
      ]);
      setCampaigns(list?.data?.campaigns || []);
      setStats(st?.data || null);
    } catch (e) {
      setErr(e.message || 'Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter]);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh active list every 10s
  useEffect(() => {
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  const sortedCampaigns = useMemo(
    () => [...campaigns].sort(
      (a, b) => new Date(b.last_event_at) - new Date(a.last_event_at),
    ),
    [campaigns],
  );

  return (
    <div className="space-y-4 p-6">
      <motion.div {...anim} className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-base-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-accent" />
            Campaigns
          </h1>
          <p className="text-xs text-base-500 mt-0.5">
            Correlated attacker activity grouped across incidents.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}>
          <RefreshCw className={cn('w-3.5 h-3.5 mr-1', loading && 'animate-spin')} />
          Refresh
        </Button>
      </motion.div>

      {stats && (
        <motion.div {...anim} className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatPill label="Active campaigns"  value={stats.active}          tone="accent" />
          <StatPill label="Critical active"   value={stats.critical_active} tone="critical" />
          <StatPill label="High active"       value={stats.high_active}     tone="high" />
          <StatPill label="Avg incidents/campaign" value={Number(stats.avg_incidents_per_active || 0).toFixed(1)} />
        </motion.div>
      )}

      <Card>
        <div className="p-3 flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setStatusFilter(f.key)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded font-medium border transition-colors',
                  statusFilter === f.key
                    ? 'bg-accent text-base-950 border-accent'
                    : 'bg-base-900 text-base-300 border-base-700 hover:border-accent/40',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 ml-2">
            {SEVERITY_FILTERS.map((f) => (
              <button
                key={f.key || 'any'}
                onClick={() => setSeverityFilter(f.key)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded font-medium border transition-colors',
                  severityFilter === f.key
                    ? 'bg-accent text-base-950 border-accent'
                    : 'bg-base-900 text-base-300 border-base-700 hover:border-accent/40',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {err && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-red-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> {err}
        </div>
      )}

      {loading && campaigns.length === 0 ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="w-5 h-5 animate-spin text-accent" />
        </div>
      ) : sortedCampaigns.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No campaigns yet"
          description="Campaigns appear when the correlation engine groups multiple incidents from the same attacker."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {sortedCampaigns.map((c) => (
            <CampaignCard key={c.campaign_id} campaign={c} onSelect={setSelected} />
          ))}
        </div>
      )}

      {selected && (
        <CampaignDrawer
          campaign={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
