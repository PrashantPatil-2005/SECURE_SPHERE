import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Shield, Eye, EyeOff, ArrowRight, Loader2, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';

const USERNAME_RE = /^[a-zA-Z0-9_.-]{3,32}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function passwordStrength(pw) {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

const STRENGTH_LABEL = ['Too short', 'Weak', 'Okay', 'Good', 'Strong'];
const STRENGTH_COLOR = ['bg-base-700', 'bg-red-500', 'bg-orange-500', 'bg-amber-400', 'bg-emerald-500'];

export default function Signup({ onSignup }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const strength = useMemo(() => passwordStrength(password), [password]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');

    if (!USERNAME_RE.test(username.trim())) {
      setError('Username must be 3-32 chars (letters, digits, _.-).');
      return;
    }
    if (!EMAIL_RE.test(email.trim())) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError('Password must be 8+ chars and contain a letter and a digit.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const data = await api.register(username.trim(), email.trim(), password);
      if (data.success) {
        sessionStorage.setItem('securisphere_token', data.token || 'authenticated');
        onSignup?.(data);
      } else {
        setError(data.message || 'Registration failed.');
      }
    } catch {
      setError('Cannot reach backend. Is it running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-base-950 px-5 transition-colors duration-200">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px] pointer-events-none [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_75%)]" />

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-[420px] bg-base-900/80 backdrop-blur-2xl border border-base-800 rounded-2xl p-9"
      >
        <div className="absolute top-0 left-10 right-10 h-0.5 bg-gradient-to-r from-transparent via-accent to-transparent rounded-full" />

        <div className="text-center mb-7">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-accent/10 border border-accent/20 mb-4">
            <Shield className="w-7 h-7 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-base-100 tracking-tight">Create Account</h1>
          <p className="text-xs text-base-500 mt-1 uppercase tracking-widest">Join SecuriSphere</p>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-base-800 bg-base-950/50 p-2.5 text-xs text-base-300">
            <span className="shrink-0">&#10005;</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={submit} className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-medium text-base-400 mb-1.5 block">Username</label>
            <input
              type="text"
              autoComplete="username"
              placeholder="3-32 chars"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-base-800 border border-base-800 text-sm text-base-100 placeholder:text-base-600 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-base-400 mb-1.5 block">Email</label>
            <input
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-base-800 border border-base-800 text-sm text-base-100 placeholder:text-base-600 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-base-400 mb-1.5 block">Password</label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="8+ chars, letter + digit"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full h-10 px-3 pr-10 rounded-lg bg-base-800 border border-base-800 text-sm text-base-100 placeholder:text-base-600 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
              />
              <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-base-500 hover:text-base-300 transition-colors" tabIndex={-1}>
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {password && (
              <div className="mt-2">
                <div className="flex gap-1">
                  {[0, 1, 2, 3].map(i => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded ${i < strength ? STRENGTH_COLOR[strength] : 'bg-base-800'} transition-colors`}
                    />
                  ))}
                </div>
                <p className="mt-1 text-[10px] uppercase tracking-wider text-base-500">{STRENGTH_LABEL[strength]}</p>
              </div>
            )}
          </div>

          <div>
            <label className="text-xs font-medium text-base-400 mb-1.5 block">Confirm Password</label>
            <input
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Re-enter password"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-base-800 border border-base-800 text-sm text-base-100 placeholder:text-base-600 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
            {confirm && password === confirm && (
              <p className="mt-1 flex items-center gap-1 text-[11px] text-emerald-400">
                <CheckCircle2 className="w-3 h-3" /> Passwords match
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-accent text-sm font-semibold text-base-950 shadow-md shadow-accent/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-accent-hover hover:shadow-accent/30 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Create Account <ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-xs text-base-500">
            Already have an account?{' '}
            <Link to="/login" className="text-accent hover:text-accent-hover transition-colors font-medium">
              Sign in
            </Link>
          </p>
        </div>

        <div className="mt-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-base-800" />
          <span className="text-[10px] uppercase tracking-widest text-base-600">Secured by SecuriSphere</span>
          <div className="h-px flex-1 bg-base-800" />
        </div>
      </motion.div>
    </div>
  );
}
