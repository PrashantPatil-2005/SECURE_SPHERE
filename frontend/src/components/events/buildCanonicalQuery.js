/**
 * Human-readable query line derived from chip state (for QueryBar).
 *
 * @param {{
 *   search?: string;
 *   layer: string;
 *   severity: string;
 *   timePreset: string;
 *   srcIp: string;
 *   timeRange: { start: number; end: number } | null;
 * }} f
 */
export function buildCanonicalQuery(f) {
  const parts = [];
  if (f.search?.trim()) parts.push(`q:"${f.search.trim()}"`);
  if (f.layer !== 'all') parts.push(`layer:${f.layer}`);
  if (f.severity !== 'all') parts.push(`severity:${f.severity}`);
  if (f.timePreset === '1h') parts.push('window:1h');
  if (f.timePreset === '24h') parts.push('window:24h');
  if (f.srcIp !== 'all') parts.push(`src:${f.srcIp}`);
  if (f.timeRange) {
    parts.push(
      `t:[${new Date(f.timeRange.start).toLocaleTimeString()}–${new Date(f.timeRange.end).toLocaleTimeString()}]`
    );
  }
  return parts.length ? parts.join(' AND ') : '∅ (all rows in time preset)';
}
