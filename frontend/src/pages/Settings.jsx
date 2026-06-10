import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Settings as SettingsIcon, User, Bell, Palette, Volume2, VolumeX, Sun, Moon,
  Lock, Activity, Monitor, Globe, Loader2, Trash2,
} from 'lucide-react';
import PageHeader from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import EmptyState from '@/components/ui/EmptyState';
import { useAppStore } from '@/stores/useAppStore';
import { useToast } from '@/components/ui/Toaster';
import { useAuth } from '@/contexts/AuthProvider';
import { api } from '@/lib/api';
import { cn, formatTimestampFull, relativeTime } from '@/lib/utils';

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security', icon: Lock },
  { id: 'sessions', label: 'Sessions', icon: Monitor },
  { id: 'audit', label: 'Audit log', icon: Activity },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'appearance', label: 'Appearance', icon: Palette },
];

export default function Settings() {
  const [params, setParams] = useSearchParams();
  const initial = TABS.find((t) => t.id === params.get('tab'))?.id || 'profile';
  const [tab, setTab] = useState(initial);
  const { user } = useAuth();

  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const density = useAppStore((s) => s.density);
  const toggleDensity = useAppStore((s) => s.toggleDensity);
  const ann = useAppStore((s) => s.ann);
  const toggleAnn = useAppStore((s) => s.toggleAnn);
  const soundEnabled = useAppStore((s) => s.soundEnabled);
  const toggleSound = useAppStore((s) => s.toggleSound);
  const soundVolume = useAppStore((s) => s.soundVolume);
  const setSoundVolume = useAppStore((s) => s.setSoundVolume);

  const switchTab = (id) => {
    setTab(id);
    setParams({ tab: id });
  };

  return (
    <div className="mx-auto max-w-4xl px-5 py-6">
      <PageHeader
        title="Settings"
        description="Personalize SecuriSphere — profile, security, alerts, appearance."
        icon={SettingsIcon}
      />

      <div className="grid grid-cols-[180px_1fr] gap-6">
        <nav className="flex flex-col gap-1" aria-label="Settings sections">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => switchTab(t.id)}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-flex items-center gap-2 rounded-md px-2.5 py-1.5 text-[12px] font-medium transition-colors',
                  active
                    ? 'bg-accent/10 text-accent'
                    : 'text-base-400 hover:bg-base-800/40 hover:text-base-200'
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {t.label}
              </button>
            );
          })}
        </nav>

        <div className="rounded-xl border border-base-800 bg-base-900/40 p-5">
          {tab === 'profile' && <ProfileTab user={user} />}
          {tab === 'security' && <SecurityTab />}
          {tab === 'sessions' && <SessionsTab />}
          {tab === 'audit' && <AuditTab />}
          {tab === 'notifications' && (
            <NotificationsTab
              soundEnabled={soundEnabled}
              toggleSound={toggleSound}
              soundVolume={soundVolume}
              setSoundVolume={setSoundVolume}
            />
          )}
          {tab === 'appearance' && (
            <AppearanceTab
              theme={theme}
              toggleTheme={toggleTheme}
              density={density}
              toggleDensity={toggleDensity}
              ann={ann}
              toggleAnn={toggleAnn}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, description, children }) {
  return (
    <div className="mb-5 last:mb-0">
      <div className="mb-2">
        <h2 className="text-sm font-semibold text-base-100">{title}</h2>
        {description && <p className="mt-0.5 text-[11px] text-base-500">{description}</p>}
      </div>
      <div className="rounded-lg border border-dashed border-base-800 bg-base-950/40 p-4">{children}</div>
    </div>
  );
}

function Row({ label, hint, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <div className="text-[12px] font-medium text-base-200">{label}</div>
        {hint && <div className="mt-0.5 text-[11px] text-base-500">{hint}</div>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function ProfileTab({ user }) {
  return (
    <Section title="Account" description="Profile info from current session.">
      <Row label="Username">
        <span className="font-mono text-[12px] text-base-200">{user?.username || '—'}</span>
      </Row>
      <Row label="Email">
        <span className="font-mono text-[12px] text-base-200">{user?.email || '—'}</span>
      </Row>
      <Row label="Role">
        <span className="font-mono text-[11px] uppercase tracking-wider text-accent">{user?.role || 'analyst'}</span>
      </Row>
    </Section>
  );
}

function SecurityTab() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const submit = async (e) => {
    e.preventDefault();
    if (next !== confirm) {
      toast.error('New password does not match confirmation');
      return;
    }
    setBusy(true);
    try {
      const res = await api.changePassword(current, next);
      if (res?.success) {
        toast.success('Password changed');
        setCurrent(''); setNext(''); setConfirm('');
      } else {
        toast.error(res?.message || 'Could not change password');
      }
    } catch {
      toast.error('Could not change password');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section title="Change password" description="Min 8 chars, must include letter + digit.">
      <form onSubmit={submit} className="flex flex-col gap-3">
        <label className="text-[11px] text-base-400">
          <span className="mb-1 block">Current password</span>
          <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" />
        </label>
        <label className="text-[11px] text-base-400">
          <span className="mb-1 block">New password</span>
          <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8} autoComplete="new-password" />
        </label>
        <label className="text-[11px] text-base-400">
          <span className="mb-1 block">Confirm new password</span>
          <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} autoComplete="new-password" />
        </label>
        <div className="flex justify-end">
          <Button type="submit" variant="primary" size="sm" disabled={busy} className="gap-1.5">
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Update password
          </Button>
        </div>
      </form>
    </Section>
  );
}

function SessionsTab() {
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const load = async () => {
    setBusy(true);
    try {
      const res = await api.listSessions();
      setRows(res?.data || []);
    } catch {
      setRows([]);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(); }, []);

  const revoke = async (fp) => {
    if (!window.confirm('Revoke this session?')) return;
    try {
      const res = await api.revokeSession(fp);
      if (res?.success) {
        toast.success('Session revoked');
        load();
      } else {
        toast.error(res?.message || 'Revoke failed');
      }
    } catch {
      toast.error('Revoke failed');
    }
  };

  if (rows === null && busy) {
    return <div className="flex items-center gap-2 text-[12px] text-base-500"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading sessions…</div>;
  }
  if (!rows || rows.length === 0) {
    return <EmptyState icon={Monitor} title="No active sessions" description="Sign in to populate this list." />;
  }

  return (
    <Section title="Active sessions" description="Revoke any session that isn't yours.">
      <ul className="divide-y divide-dashed divide-base-800">
        {rows.map((s) => (
          <li key={s.token_fp} className="flex items-start justify-between gap-3 py-2.5">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Globe className="h-3.5 w-3.5 text-base-500" />
                <span className="font-mono text-[12px] text-base-200">{s.ip || 'unknown'}</span>
                {s.current && (
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-emerald-300">
                    current
                  </span>
                )}
              </div>
              <div className="mt-0.5 truncate font-mono text-[10px] text-base-500">{s.user_agent || 'unknown agent'}</div>
              <div className="mt-0.5 font-mono text-[10px] text-base-600">
                Issued {s.issued_at ? relativeTime(s.issued_at) : '—'} · fp {s.token_fp}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => revoke(s.token_fp)}
              disabled={s.current}
              title={s.current ? 'Sign out via the profile menu' : 'Revoke'}
              className="text-red-300 hover:text-red-200"
            >
              <Trash2 className="h-3.5 w-3.5" /> Revoke
            </Button>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function AuditTab() {
  const [rows, setRows] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.listAuditLogins(50)
      .then((res) => { if (!cancelled) setRows(res?.data || []); })
      .catch(() => { if (!cancelled) setRows([]); });
    return () => { cancelled = true; };
  }, []);

  if (rows === null) {
    return <div className="flex items-center gap-2 text-[12px] text-base-500"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading audit log…</div>;
  }
  if (!rows.length) {
    return <EmptyState icon={Activity} title="No audit rows" description="Login attempts will appear once recorded." />;
  }
  return (
    <Section title="Login audit" description="Recent sign-in attempts (last 50).">
      <ul className="divide-y divide-dashed divide-base-800">
        {rows.map((r) => (
          <li key={r.id} className="flex items-start justify-between gap-3 py-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'inline-flex h-1.5 w-1.5 rounded-full',
                    r.success ? 'bg-emerald-400' : 'bg-red-400'
                  )}
                />
                <span className="font-mono text-[12px] text-base-200">{r.username}</span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-base-500">{r.reason || (r.success ? 'login' : 'fail')}</span>
              </div>
              <div className="mt-0.5 truncate font-mono text-[10px] text-base-500">
                {r.ip || 'no ip'} · {r.user_agent || 'unknown agent'}
              </div>
            </div>
            <span className="shrink-0 font-mono text-[10px] text-base-600" title={r.at ? formatTimestampFull(r.at) : ''}>
              {r.at ? relativeTime(r.at) : '—'}
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function NotificationsTab({ soundEnabled, toggleSound, soundVolume, setSoundVolume }) {
  return (
    <Section title="Critical alert sound" description="Plays a synth chime when a critical incident lands.">
      <Row label="Sound enabled" hint="Browser must allow audio after first user interaction.">
        <Button
          variant={soundEnabled ? 'primary' : 'secondary'}
          size="sm"
          onClick={toggleSound}
          className="gap-1.5"
        >
          {soundEnabled ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
          {soundEnabled ? 'On' : 'Off'}
        </Button>
      </Row>
      <Row label="Volume">
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={soundVolume}
          onChange={(e) => setSoundVolume(parseFloat(e.target.value))}
          aria-label="Alert volume"
          className="h-1 w-40 cursor-pointer appearance-none rounded-full bg-base-800 accent-accent"
        />
      </Row>
    </Section>
  );
}

function AppearanceTab({ theme, toggleTheme, density, toggleDensity, ann, toggleAnn }) {
  return (
    <>
      <Section title="Theme">
        <Row label="Color scheme" hint="Light/dark — applies instantly.">
          <Button variant="secondary" size="sm" onClick={toggleTheme} className="gap-1.5">
            {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            {theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
          </Button>
        </Row>
      </Section>
      <Section title="Layout">
        <Row label="Density" hint="Comfy or compact spacing.">
          <Button variant="secondary" size="sm" onClick={toggleDensity}>
            {density === 'compact' ? 'Compact' : 'Comfy'}
          </Button>
        </Row>
        <Row label="Annotations" hint="Show inline hints on dashboards.">
          <Button variant="secondary" size="sm" onClick={toggleAnn}>
            {ann === 'on' ? 'On' : 'Off'}
          </Button>
        </Row>
      </Section>
    </>
  );
}
