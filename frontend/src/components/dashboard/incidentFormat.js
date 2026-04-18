import { safeString } from '@/lib/utils';

function shortService(name) {
  const s = safeString(name);
  if (!s) return '';
  return s.replace(/-service$/i, '').replace(/-/g, ' ');
}

/**
 * @param {Record<string, unknown>} inc
 * @returns {string}
 */
export function formatIncidentPath(inc) {
  const path = inc?.service_path;
  if (Array.isArray(path) && path.length > 0) {
    return path.map(shortService).join(' → ');
  }
  const layers = inc?.layers_involved;
  if (Array.isArray(layers) && layers.length > 0) {
    return layers.map((x) => safeString(x)).join(' → ');
  }
  return '';
}

/**
 * @param {Record<string, unknown>} inc
 * @returns {number}
 */
export function killChainStepCount(inc) {
  const k = inc?.kill_chain_steps;
  if (Array.isArray(k)) return k.length;
  if (typeof k === 'number' && !Number.isNaN(k)) return k;
  return 0;
}
