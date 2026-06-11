import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Shield, Eye, EyeOff, ArrowRight, Loader2,
  Zap, Network, Target, CheckCircle2,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthProvider';

const FEATURES = [
  { icon: Zap,        text: 'Real-time kill-chain correlation' },
  { icon: Network,    text: 'Live service topology mapping' },
  { icon: Target,     text: 'MITRE ATT&CK coverage tracking' },
  { icon: Shield,     text: 'WAF proxy with automated blocking' },
];

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password.trim()) {
      setError('Enter both username and password.');
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password, remember);
    } catch (err) {
      setError(err?.message || 'Cannot reach backend. Is it running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-base-950 transition-colors duration-200">

      {/* ── Left panel — branding ─────────────────────────────────────── */}
      <div className="relative hidden lg:flex lg:w-[480px] xl:w-[540px] flex-col justify-between overflow-hidden border-r border-base-800 bg-base-900 p-12">
        {/* Subtle grid overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.025]"
          style={{
            backgroundImage:
              'linear-gradient(var(--base-400) 1px, transparent 1px), linear-gradient(90deg, var(--base-400) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        {/* Accent radial glow */}
        <div
          className="pointer-events-none absolute -left-24 top-1/3 h-[500px] w-[500px] rounded-full opacity-[0.06]"
          style={{
            background: 'radial-gradient(circle, var(--accent) 0%, transparent 70%)',
          }}
        />

        {/* Top: brand */}
        <div className="relative">
          <div className="flex items-center gap-3 mb-12">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl border"
              style={{
                borderColor: 'var(--sev-critical-border)',
                background: 'linear-gradient(135deg, rgba(239,68,68,0.18), rgba(239,68,68,0.06))',
              }}
            >
              <Shield className="h-5 w-5" style={{ color: 'var(--sev-critical)' }} />
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-base-100">SecuriSphere</div>
              <div className="type-eyebrow font-mono">v2.0 · SOC Platform</div>
            </div>
          </div>

          <h2 className="text-3xl font-bold leading-tight tracking-tight text-base-100">
            Security Operations<br />
            <span style={{ color: 'var(--accent)' }}>at machine speed.</span>
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-base-400">
            Correlate threats, track attackers, and respond — all from one unified dashboard built for modern SOC analysts.
          </p>
        </div>

        {/* Middle: features */}
        <div className="relative space-y-3">
          {FEATURES.map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-3">
              <div
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                style={{ background: 'var(--accent-muted)' }}
              >
                <Icon className="h-3.5 w-3.5" style={{ color: 'var(--accent)' }} />
              </div>
              <span className="text-sm text-base-300">{text}</span>
              <CheckCircle2 className="ml-auto h-3.5 w-3.5 shrink-0 text-base-600" />
            </div>
          ))}
        </div>

        {/* Bottom: footer */}
        <div className="relative">
          <div className="h-px w-full bg-base-800 mb-4" />
          <p className="type-eyebrow font-mono text-base-600">
            Enterprise-grade threat detection
          </p>
        </div>
      </div>

      {/* ── Right panel — form ────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        {/* Mobile logo */}
        <div className="mb-8 flex items-center gap-2.5 lg:hidden">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg border"
            style={{
              borderColor: 'var(--sev-critical-border)',
              background: 'linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05))',
            }}
          >
            <Shield className="h-4 w-4" style={{ color: 'var(--sev-critical)' }} />
          </div>
          <span className="text-sm font-bold tracking-tight text-base-100">SecuriSphere</span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="w-full max-w-[380px]"
        >
          {/* Heading */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-base-100">Sign in</h1>
            <p className="type-caption mt-1.5">
              Enter your credentials to access the SOC dashboard.
            </p>
          </div>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-5 flex items-start gap-2.5 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300"
            >
              <span className="mt-px shrink-0 font-mono">✕</span>
              <span>{error}</span>
            </motion.div>
          )}

          <form onSubmit={submit} className="flex flex-col gap-5">
            {/* Username */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="login-username" className="type-eyebrow">
                Username
              </label>
              <input
                id="login-username"
                type="text"
                autoComplete="username"
                placeholder="your-username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="h-10 w-full rounded-lg border border-base-800 bg-base-900/60 px-3 text-sm text-base-100 placeholder:text-base-600 outline-none transition-all focus:border-accent/60 focus:ring-2 focus:ring-accent/15"
              />
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="type-eyebrow">
                  Password
                </label>
                <button
                  type="button"
                  className="text-xs text-accent transition-colors hover:text-accent-hover"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPw ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="h-10 w-full rounded-lg border border-base-800 bg-base-900/60 px-3 pr-10 text-sm text-base-100 placeholder:text-base-600 outline-none transition-all focus:border-accent/60 focus:ring-2 focus:ring-accent/15"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-base-500 transition-colors hover:text-base-300"
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Remember me */}
            <label className="flex cursor-pointer select-none items-center gap-2.5">
              <input
                type="checkbox"
                checked={remember}
                onChange={e => setRemember(e.target.checked)}
                className="sr-only"
              />
              <span
                aria-hidden="true"
                className="flex h-4 w-4 items-center justify-center rounded border transition-all"
                style={{
                  background: remember ? 'var(--accent)' : 'transparent',
                  borderColor: remember ? 'var(--accent)' : 'var(--base-700)',
                }}
              >
                {remember && (
                  <svg className="h-2.5 w-2.5" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </span>
              <span className="text-xs text-base-400">Keep me signed in</span>
            </label>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="mt-1 flex h-10 w-full items-center justify-center gap-2 rounded-lg text-sm font-semibold transition-all duration-200 hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-50"
              style={{
                background: 'var(--accent)',
                color: '#fff',
                boxShadow: '0 4px 14px -4px rgba(129,140,248,0.5)',
              }}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>Sign in <ArrowRight className="h-4 w-4" /></>
              )}
            </button>
          </form>

          <p className="type-caption mt-6 text-center">
            Accounts are created by administrators.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
