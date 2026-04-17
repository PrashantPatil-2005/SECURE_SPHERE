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

export function formatTimestamp(iso) {
  if (!iso) return '\u2014';
  return new Date(iso).toLocaleTimeString();
}

export function formatTimestampFull(iso) {
  if (!iso) return '\u2014';
  return new Date(iso).toLocaleString();
}

export function relativeTime(iso) {
  if (!iso) return '';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 0) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function severityColor(severity) {
  switch (getSeverityString(severity)) {
    case 'critical': return '#c14953';
    case 'high':     return '#b8753a';
    case 'medium':   return '#b59441';
    case 'low':      return '#5f8c6e';
    default:         return '#5f667a';
  }
}

export function severityClass(severity) {
  switch (getSeverityString(severity)) {
    case 'critical': return 'text-severity-critical bg-red-500/10 border-red-500/20';
    case 'high': return 'text-severity-high bg-orange-500/10 border-orange-500/20';
    case 'medium': return 'text-severity-medium bg-yellow-500/10 border-yellow-500/20';
    case 'low': return 'text-severity-low bg-green-500/10 border-green-500/20';
    default: return 'text-severity-info bg-cyan-500/10 border-cyan-500/20';
  }
}

export function threatLevelColor(level) {
  switch (level?.toLowerCase()) {
    case 'critical':    return '#8a5e9a';
    case 'threatening': return '#c14953';
    case 'suspicious':  return '#b59441';
    case 'normal':      return '#5f8c6e';
    default:            return '#5f8c6e';
  }
}

export function layerColor(layer) {
  switch (layer?.toLowerCase()) {
    case 'network': return '#6b86b3';
    case 'api':     return '#8a7dad';
    case 'auth':    return '#5f8c6e';
    case 'browser': return '#b8753a';
    default:        return '#5f667a';
  }
}
