import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function safeString(val) {
  if (val == null) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'object' && val.level) return val.level;
  return String(val);
}

export function getSeverityString(severity) {
  if (!severity) return 'default';
  if (typeof severity === 'string') return severity.toLowerCase();
  return (severity.level || 'default').toLowerCase();
}

// Backend emits `datetime.utcnow().isoformat()` (naive — no "Z"). Browser
// parses naive ISO as LOCAL, producing a UTC-offset skew (e.g. IST viewers
// saw fresh incidents as "5h ago"). Treat any naive ISO as UTC.
function parseServerTime(iso) {
  if (!iso) return null;
  const s = String(iso);
  // Already has timezone (Z or ±HH:MM) — parse as-is.
  if (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s);
  return new Date(s + 'Z');
}

export function formatTimestamp(iso) {
  if (!iso) return '\u2014';
  const d = parseServerTime(iso);
  return d ? d.toLocaleTimeString() : '\u2014';
}

export function formatTimestampFull(iso) {
  if (!iso) return '\u2014';
  const d = parseServerTime(iso);
  return d ? d.toLocaleString() : '\u2014';
}

export function relativeTime(iso) {
  if (!iso) return '';
  const d = parseServerTime(iso);
  if (!d) return '';
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diff < 0) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function severityColor(severity) {
  switch (getSeverityString(severity)) {
    case 'critical':
      return '#ef4444';
    case 'high':
      return '#f97316';
    case 'medium':
      return '#eab308';
    case 'low':
      return '#22d3ee';
    default:
      return 'var(--base-500)';
  }
}

export function severityClass(severity) {
  switch (getSeverityString(severity)) {
    case 'critical':
      return 'text-red-400 bg-red-500/10 border-red-500/30';
    case 'high':
      return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
    case 'medium':
      return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    case 'low':
      return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
    default:
      return 'text-base-500 bg-base-900/50 border-base-800';
  }
}

export function threatLevelColor(level) {
  switch (level?.toLowerCase()) {
    case 'critical':
      return '#ef4444';
    case 'threatening':
      return '#f97316';
    case 'suspicious':
      return '#eab308';
    case 'normal':
      return '#10b981';
    default:
      return '#64748b';
  }
}

export function layerColor(layer) {
  switch (layer?.toLowerCase()) {
    case 'network':
      return '#22d3ee';
    case 'api':
      return '#a855f7';
    case 'auth':
      return '#f59e0b';
    case 'browser':
      return '#34d399';
    default:
      return 'var(--base-500)';
  }
}
