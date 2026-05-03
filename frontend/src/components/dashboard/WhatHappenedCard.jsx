import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { getSeverityString, relativeTime, safeString } from '@/lib/utils';

function pathFrom(featured) {
  const candidates = [
    featured?.attack_path,
    featured?.path,
    featured?.service_path,
    featured?.affected_services,
  ];
  for (const c of candidates) {
    if (Array.isArray(c) && c.length > 0) return c.map((x) => safeString(x)).filter(Boolean);
  }
  const svc = safeString(featured?.target_service || featured?.service);
  return svc ? [svc] : [];
}

function mitreFrom(featured) {
  const c = featured?.mitre_techniques || featured?.mitre || featured?.techniques;
  if (Array.isArray(c)) {
    return c
      .map((t) => (typeof t === 'string' ? t : safeString(t?.id || t?.technique_id)))
      .filter(Boolean)
      .slice(0, 6);
  }
  return [];
}

function descriptionFrom(featured) {
  return (
    safeString(featured?.description) ||
    safeString(featured?.summary) ||
    safeString(featured?.detail) ||
    'No description available.'
  );
}

function titleFrom(featured) {
  return (
    safeString(featured?.title) ||
    safeString(featured?.scenario_label) ||
    safeString(featured?.incident_type) ||
    'Active incident'
  );
}

function timestampFrom(featured) {
  return featured?.last_seen || featured?.detected_at || featured?.created_at || featured?.ts;
}

function riskFrom(featured) {
  const r = featured?.risk_score ?? featured?.risk ?? featured?.severity_score;
  return typeof r === 'number' ? Math.round(r) : null;
}

export default function WhatHappenedCard({ incident }) {
  if (!incident) return null;

  const sev = getSeverityString(incident?.severity) || 'critical';
  const path = pathFrom(incident);
  const mitre = mitreFrom(incident);
  const risk = riskFrom(incident);
  const ts = timestampFrom(incident);
  const isCritical = sev === 'critical';

  return (
    <Card glow={isCritical} className="overflow-hidden p-0">
      <div
        className="flex items-center justify-between border-b border-base-800 px-4 py-2.5"
        style={{
          background: isCritical
            ? 'linear-gradient(to right, rgba(239,68,68,0.07), transparent)'
            : 'transparent',
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className={isCritical ? 'dot-pulse inline-block h-2 w-2 rounded-full' : 'inline-block h-2 w-2 rounded-full'}
            style={{
              background: 'var(--sev-critical)',
              '--dot-color': 'rgba(239,68,68,0.6)',
            }}
          />
          <span className="text-[11px] font-bold uppercase tracking-[0.07em] text-base-300">
            What Happened?
          </span>
          <Badge variant={sev}>Live</Badge>
        </div>
        {ts && (
          <span className="font-mono text-[10px] text-base-600">{relativeTime(ts)}</span>
        )}
      </div>

      <div className="flex flex-col gap-3.5 px-4 py-3 md:flex-row md:items-start md:gap-4">
        <div className="min-w-0 flex-1">
          <p className="mb-1.5 text-[13px] font-semibold leading-snug text-base-100">
            {titleFrom(incident)}
          </p>
          <p className="text-[12px] leading-relaxed text-base-400">{descriptionFrom(incident)}</p>

          {path.length > 0 && (
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              {path.map((s, i) => (
                <span key={`${s}-${i}`} className="inline-flex items-center gap-1.5">
                  <span className="rounded-md border border-base-700 bg-base-800 px-2 py-0.5 font-mono text-[11px] text-base-300">
                    {s}
                  </span>
                  {i < path.length - 1 && (
                    <span className="text-[11px] text-base-600">→</span>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col gap-2 md:min-w-[140px]">
          {risk != null && (
            <div
              className="rounded-lg border px-3 py-1.5 text-center"
              style={{
                background: 'var(--sev-critical-bg)',
                borderColor: 'var(--sev-critical-border)',
              }}
            >
              <div
                className="text-[10px] font-semibold uppercase tracking-[0.07em]"
                style={{ color: 'var(--sev-critical)' }}
              >
                Risk Score
              </div>
              <div
                className="font-mono text-[20px] font-bold leading-none"
                style={{ color: 'var(--sev-critical)' }}
              >
                {risk}
              </div>
            </div>
          )}
          {mitre.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {mitre.map((t) => (
                <span
                  key={t}
                  className="rounded border border-white/10 bg-white/[0.05] px-1.5 py-0.5 font-mono text-[9px] text-base-300"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
