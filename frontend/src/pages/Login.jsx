import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

export default function Login({ onLogin }) {
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
      const data = await api.login(username.trim(), password);
      if (data.success) {
        const store = remember ? localStorage : sessionStorage;
        store.setItem('securisphere_token', data.token || 'authenticated');
        onLogin(data);
      } else {
        setError(data.message || 'Invalid credentials.');
      }
    } catch {
      setError('Cannot reach backend. Is it running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-base-950 px-5 transition-colors duration-200">
      {/* Subtle grid — no neon orbs */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px] pointer-events-none [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_75%)]" />

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-[400px] bg-base-900/80 backdrop-blur-2xl border border-base-800 rounded-2xl p-9"
      >
        {/* Accent line */}
        <div className="absolute top-0 left-10 right-10 h-0.5 bg-gradient-to-r from-transparent via-accent to-transparent rounded-full" />

        {/* Logo */}
        <div className="text-center mb-7">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-accent/10 border border-accent/20 mb-4">
            <Shield className="w-7 h-7 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-base-100 tracking-tight">SecuriSphere</h1>
          <p className="text-xs text-base-500 mt-1 uppercase tracking-widest">Authentication Required</p>
        </div>

        {/* Error */}
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
              placeholder="Enter username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-base-800 border border-base-800 text-sm text-base-100 placeholder:text-base-600 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-base-400 mb-1.5 block">Password</label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full h-10 px-3 pr-10 rounded-lg bg-base-800 border border-base-800 text-sm text-base-100 placeholder:text-base-600 outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
              />
              <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-base-500 hover:text-base-300 transition-colors" tabIndex={-1}>
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} className="sr-only" />
              <div className={`w-4 h-4 rounded border ${remember ? 'bg-accent border-accent' : 'border-base-800 bg-base-950/40'} flex items-center justify-center transition-all`}>
                {remember && <svg className="h-2.5 w-2.5 text-base-950" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>}
              </div>
              <span className="text-xs text-base-400">Remember me</span>
            </label>
            <button type="button" className="text-xs text-accent hover:text-accent-hover transition-colors">Forgot password?</button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-accent text-sm font-semibold text-base-950 shadow-md shadow-accent/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-accent-hover hover:shadow-accent/30 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Sign In <ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>

        <div className="mt-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-base-800" />
          <span className="text-[10px] uppercase tracking-widest text-base-600">Secured by SecuriSphere</span>
          <div className="h-px flex-1 bg-base-800" />
        </div>
      </motion.div>
    </div>
  );
}
