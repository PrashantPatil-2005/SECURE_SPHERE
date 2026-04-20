import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Server, Webhook, ExternalLink, Shield, ShieldCheck, ShieldOff, ShieldAlert, Copy, RefreshCw, Loader2, Lock, Globe, Bot, ListChecks, Ban } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

export default function System({ systemStatus = {}, onRefresh }) {
  const [webhook, setWebhook] = useState('');

  // ── Protected Asset / WAF proxy state ────────────────────────────────
  const [proxyCfg, setProxyCfg] = useState(null);
  const [proxyStats, setProxyStats] = useState({});
  const [proxyPublicUrl, setProxyPublicUrl] = useState('');
  const [proxyTlsUrl, setProxyTlsUrl] = useState('');
  const [upstreamInput, setUpstreamInput] = useState('');
  const [wafEnabled, setWafEnabled] = useState(true);
  const [rateLimit, setRateLimit] = useState(600);
  const [tlsEnabled, setTlsEnabled] = useState(false);
  const [captchaEnabled, setCaptchaEnabled] = useState(false);
  const [geoEnabled, setGeoEnabled] = useState(false);
  const [allowText, setAllowText] = useState('');
  const [blockText, setBlockText] = useState('');
  const [geoText, setGeoText] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  const fetchProxy = useCallback(async () => {
    try {
      const d = await api.getProxyConfig();
      setProxyCfg(d.config || {});
      setProxyStats(d.stats || {});
      setProxyPublicUrl(d.public_url || '');
      setProxyTlsUrl(d.public_tls_url || '');
      const c = d.config || {};
      if (c.upstream) setUpstreamInput(c.upstream);
      if (typeof c.waf_enabled === 'boolean') setWafEnabled(c.waf_enabled);
      if (c.rate_limit_rpm) setRateLimit(c.rate_limit_rpm);
      setTlsEnabled(!!c.tls_enabled);
      setCaptchaEnabled(!!c.captcha_enabled);
      setGeoEnabled(!!c.geo_enabled);
      setAllowText((c.ip_allowlist || []).join('\n'));
      setBlockText((c.ip_blocklist || []).join('\n'));
      setGeoText((c.geo_blocklist || []).join(', '));
    } catch (e) {
      setSaveMsg({ type: 'err', text: `Failed to load proxy config: ${e.message}` });
    }
  }, []);

  useEffect(() => {
    fetchProxy();
    const id = setInterval(fetchProxy, 5000);
    return () => clearInterval(id);
  }, [fetchProxy]);

  const parseList = (text) =>
    text.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);

  const handleSaveProxy = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const res = await api.setProxyConfig({
        upstream: upstreamInput,
        waf_enabled: wafEnabled,
        rate_limit_rpm: rateLimit,
        tls_enabled: tlsEnabled,
        captcha_enabled: captchaEnabled,
        geo_enabled: geoEnabled,
        ip_allowlist: parseList(allowText),
        ip_blocklist: parseList(blockText),
        geo_blocklist: parseList(geoText).map((s) => s.toUpperCase()),
      });
      setSaveMsg({ type: 'ok', text: `Saved. WAF protecting ${res.data?.upstream || '—'}` });
      fetchProxy();
    } catch (e) {
      setSaveMsg({ type: 'err', text: e.message });
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = (text) => {
    if (!text) return;
    try {
      navigator.clipboard?.writeText(text);
      setSaveMsg({ type: 'ok', text: 'Copied proxy URL to clipboard' });
      setTimeout(() => setSaveMsg(null), 1500);
    } catch {}
  };

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

      {/* Protected Asset / WAF Proxy */}
      <Card className="overflow-hidden">
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              {wafEnabled && proxyCfg?.upstream ? (
                <ShieldCheck className="h-5 w-5 text-emerald-400" />
              ) : !proxyCfg?.upstream ? (
                <ShieldAlert className="h-5 w-5 text-amber-400" />
              ) : (
                <ShieldOff className="h-5 w-5 text-base-500" />
              )}
              <CardTitle>Protected Asset</CardTitle>
              {proxyCfg?.upstream && (
                <Badge variant={wafEnabled ? 'resolved' : 'investigating'}>
                  {wafEnabled ? 'WAF Active' : 'Passthrough'}
                </Badge>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={fetchProxy} title="Refresh stats">
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-xs text-base-400">
            Route traffic through the SecuriSphere reverse proxy. Requests are inspected by the WAF,
            blocked when malicious patterns match, and every event streams into the correlation engine.
          </p>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <StatPill label="Requests"  value={proxyStats.requests ?? 0}  color="text-base-200" />
            <StatPill label="Blocked"   value={proxyStats.blocked  ?? 0}  color="text-red-400" />
            <StatPill label="Rate-limit" value={proxyStats.ratelimit ?? 0} color="text-amber-400" />
            <StatPill label="SQLi"      value={proxyStats.sqli ?? 0}      color="text-orange-400" />
            <StatPill label="XSS"       value={proxyStats.xss  ?? 0}      color="text-pink-400" />
            <StatPill label="Traversal" value={proxyStats.traversal ?? 0} color="text-violet-400" />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[11px] font-medium text-base-300">Upstream URL (site to protect)</label>
            <div className="flex gap-2">
              <Input
                placeholder="https://your-site.example.com"
                value={upstreamInput}
                onChange={(e) => setUpstreamInput(e.target.value)}
                className="flex-1 text-xs"
              />
              <Button variant="primary" size="sm" onClick={handleSaveProxy} disabled={saving || !upstreamInput.trim()}>
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />}
                {saving ? 'Saving…' : 'Protect'}
              </Button>
            </div>
            <p className="font-mono text-[10px] text-base-600">
              localhost / 127.0.0.1 are blocked to prevent SSRF loopback.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="flex items-center justify-between gap-3 rounded-md border border-dashed border-base-800 bg-base-950/40 p-2.5">
              <div>
                <div className="text-[11px] font-medium text-base-200">WAF Rules</div>
                <div className="text-[10px] text-base-500">SQLi · XSS · Traversal · CmdInj · Scanner</div>
              </div>
              <input
                type="checkbox"
                checked={wafEnabled}
                onChange={(e) => setWafEnabled(e.target.checked)}
                className="h-4 w-4 accent-emerald-500"
              />
            </label>

            <div className="rounded-md border border-dashed border-base-800 bg-base-950/40 p-2.5">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[11px] font-medium text-base-200">Rate limit (req/min per IP)</span>
                <span className="font-mono text-[11px] tabular-nums text-base-300">{rateLimit}</span>
              </div>
              <input
                type="range"
                min="10"
                max="6000"
                step="10"
                value={rateLimit}
                onChange={(e) => setRateLimit(Number(e.target.value))}
                className="w-full accent-accent"
              />
            </div>
          </div>

          {/* ── Advanced WAF extras ─────────────────────────────────── */}
          <div className="rounded-md border border-base-800 bg-base-950/40 p-3">
            <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-base-300">
              <ListChecks className="h-3.5 w-3.5 text-accent" /> Advanced Policy
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <label className="flex items-center justify-between gap-3 rounded-md border border-base-800 bg-base-950/60 p-2.5">
                <div className="flex items-center gap-2">
                  <Lock className="h-3.5 w-3.5 text-cyan-400" />
                  <div>
                    <div className="text-[11px] font-medium text-base-200">TLS (HTTPS)</div>
                    <div className="text-[10px] text-base-500">Self-signed cert on :8443</div>
                  </div>
                </div>
                <input type="checkbox" checked={tlsEnabled}
                  onChange={(e) => setTlsEnabled(e.target.checked)}
                  className="h-4 w-4 accent-cyan-500" />
              </label>

              <label className="flex items-center justify-between gap-3 rounded-md border border-base-800 bg-base-950/60 p-2.5">
                <div className="flex items-center gap-2">
                  <Bot className="h-3.5 w-3.5 text-fuchsia-400" />
                  <div>
                    <div className="text-[11px] font-medium text-base-200">CAPTCHA on rate-limit</div>
                    <div className="text-[10px] text-base-500">PoW challenge instead of 429</div>
                  </div>
                </div>
                <input type="checkbox" checked={captchaEnabled}
                  onChange={(e) => setCaptchaEnabled(e.target.checked)}
                  className="h-4 w-4 accent-fuchsia-500" />
              </label>

              <label className="flex items-center justify-between gap-3 rounded-md border border-base-800 bg-base-950/60 p-2.5">
                <div className="flex items-center gap-2">
                  <Globe className="h-3.5 w-3.5 text-amber-400" />
                  <div>
                    <div className="text-[11px] font-medium text-base-200">Geo-block</div>
                    <div className="text-[10px] text-base-500">Needs CDN country header</div>
                  </div>
                </div>
                <input type="checkbox" checked={geoEnabled}
                  onChange={(e) => setGeoEnabled(e.target.checked)}
                  className="h-4 w-4 accent-amber-500" />
              </label>
            </div>

            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
              <div>
                <label className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                  <ShieldCheck className="h-3 w-3" /> IP allowlist (CIDR)
                </label>
                <textarea
                  value={allowText}
                  onChange={(e) => setAllowText(e.target.value)}
                  placeholder="10.0.0.0/8&#10;192.168.1.5"
                  rows={4}
                  className="w-full rounded-md border border-base-800 bg-base-950/60 px-2 py-1.5 font-mono text-[11px] text-base-200 placeholder:text-base-700 focus:border-emerald-500/40 focus:outline-none"
                />
                <p className="mt-1 text-[10px] text-base-600">Bypass all WAF checks. One per line.</p>
              </div>
              <div>
                <label className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-red-400">
                  <Ban className="h-3 w-3" /> IP blocklist (CIDR)
                </label>
                <textarea
                  value={blockText}
                  onChange={(e) => setBlockText(e.target.value)}
                  placeholder="203.0.113.0/24"
                  rows={4}
                  className="w-full rounded-md border border-base-800 bg-base-950/60 px-2 py-1.5 font-mono text-[11px] text-base-200 placeholder:text-base-700 focus:border-red-500/40 focus:outline-none"
                />
                <p className="mt-1 text-[10px] text-base-600">Hard-deny at edge, before rules.</p>
              </div>
              <div>
                <label className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-amber-400">
                  <Globe className="h-3 w-3" /> Country blocklist (ISO-2)
                </label>
                <textarea
                  value={geoText}
                  onChange={(e) => setGeoText(e.target.value)}
                  placeholder="CN, RU, KP"
                  rows={4}
                  className="w-full rounded-md border border-base-800 bg-base-950/60 px-2 py-1.5 font-mono text-[11px] uppercase text-base-200 placeholder:text-base-700 focus:border-amber-500/40 focus:outline-none"
                />
                <p className="mt-1 text-[10px] text-base-600">Reads CF-IPCountry / CloudFront-Viewer-Country.</p>
              </div>
            </div>

            <div className="mt-3 flex justify-end">
              <Button variant="primary" size="sm" onClick={handleSaveProxy} disabled={saving}>
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />}
                {saving ? 'Saving…' : 'Save Policy'}
              </Button>
            </div>
          </div>

          {proxyCfg?.upstream && (
            <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                Public Proxy Endpoint
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded bg-base-950/60 px-2 py-1 font-mono text-[11px] text-base-100">
                  {proxyPublicUrl || 'http://localhost:8088'}
                </code>
                <Button variant="secondary" size="sm" onClick={() => handleCopy(proxyPublicUrl || 'http://localhost:8088')}>
                  <Copy className="h-3 w-3" />
                </Button>
                <a
                  href={proxyPublicUrl || 'http://localhost:8088'}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded border border-base-800 bg-base-950/60 px-2 py-1 font-mono text-[10px] text-base-300 hover:border-accent/40 hover:text-accent"
                >
                  Open <ExternalLink className="h-2.5 w-2.5" />
                </a>
              </div>
              {tlsEnabled && proxyTlsUrl && (
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 truncate rounded bg-base-950/60 px-2 py-1 font-mono text-[11px] text-cyan-300">
                    {proxyTlsUrl}
                  </code>
                  <Button variant="secondary" size="sm" onClick={() => handleCopy(proxyTlsUrl)}>
                    <Copy className="h-3 w-3" />
                  </Button>
                  <a
                    href={proxyTlsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded border border-cyan-500/30 bg-cyan-500/5 px-2 py-1 font-mono text-[10px] text-cyan-300 hover:border-cyan-500/60"
                  >
                    Open TLS <Lock className="h-2.5 w-2.5" />
                  </a>
                </div>
              )}
              <p className="mt-2 text-[10px] text-base-500">
                Send traffic to the endpoint above — it forwards to{' '}
                <span className="font-mono text-base-300">{proxyCfg.upstream}</span>. In production,
                point DNS for your domain at the proxy host.
                {tlsEnabled && ' Browsers will warn on the self-signed TLS cert — replace with a real cert for production.'}
              </p>
            </div>
          )}

          {saveMsg && (
            <div
              className={cn(
                'rounded-md border px-3 py-2 text-[11px]',
                saveMsg.type === 'ok'
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                  : 'border-red-500/30 bg-red-500/10 text-red-300'
              )}
            >
              {saveMsg.text}
            </div>
          )}
        </CardContent>
      </Card>

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

function StatPill({ label, value, color }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-dashed border-base-800 bg-base-950/40 px-3 py-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-base-500">{label}</span>
      <span className={cn('font-mono text-sm font-bold tabular-nums', color)}>{value}</span>
    </div>
  );
}
