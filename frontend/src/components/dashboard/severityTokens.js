import { getSeverityString } from '@/lib/utils';

/** Tailwind-only severity accents — red reserved for critical */
export const SEVERITY_DOT = {
  critical: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.55)]',
  high: 'bg-base-300 shadow-[0_0_4px_rgba(0,0,0,0.2)] dark:shadow-[0_0_6px_rgba(255,255,255,0.12)]',
  medium: 'bg-base-400 shadow-[0_0_4px_rgba(0,0,0,0.15)] dark:shadow-[0_0_5px_rgba(255,255,255,0.08)]',
  low: 'bg-base-500 shadow-[0_0_3px_rgba(0,0,0,0.12)]',
  default: 'bg-base-600',
};

export function normalizeSeverity(severity) {
  const s = getSeverityString(severity);
  if (['critical', 'high', 'medium', 'low'].includes(s)) return s;
  return 'default';
}

export function severityDotClass(severity) {
  return SEVERITY_DOT[normalizeSeverity(severity)] || SEVERITY_DOT.default;
}
