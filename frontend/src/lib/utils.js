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
    case 'medium':
    case 'low':
    default:
      return 'var(--base-500)';
  }
}

export function severityClass(severity) {
  switch (getSeverityString(severity)) {
    case 'critical':
      return 'text-severity-critical bg-red-500/10 border-red-500/25';
    case 'high':
      return 'text-base-200 bg-base-800/40 border-base-700';
    case 'medium':
      return 'text-base-300 bg-base-800/30 border-base-700';
    case 'low':
      return 'text-base-400 bg-base-800/20 border-base-800';
    default:
      return 'text-base-500 bg-base-900/50 border-base-800';
  }
}

export function threatLevelColor(level) {
  switch (level?.toLowerCase()) {
    case 'critical':
      return '#ef4444';
    case 'threatening':
      return 'var(--base-400)';
    case 'suspicious':
      return 'var(--base-500)';
    case 'normal':
      return 'var(--base-600)';
    default:
      return 'var(--base-600)';
  }
}

export function layerColor(layer) {
  switch (layer?.toLowerCase()) {
    case 'network':
      return 'var(--base-400)';
    case 'api':
      return 'var(--base-500)';
    case 'auth':
      return 'var(--base-300)';
    case 'browser':
      return 'var(--base-500)';
    default:
      return 'var(--base-500)';
  }
}
