import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Download, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/input';
import { cn, severityColor, formatTimestampFull, layerColor, getSeverityString, safeString } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

export default function Events({ events }) {
  const [search, setSearch] = useState('');
  const [layerFilter, setLayerFilter] = useState('all');
  const [sevFilter, setSevFilter] = useState('all');
  const [expanded, setExpanded] = useState(null);

  const filtered = useMemo(() => {
    return events.filter(ev => {
      if (layerFilter !== 'all' && safeString(ev.source_layer).toLowerCase() !== layerFilter) return false;
      if (sevFilter !== 'all' && getSeverityString(ev.severity) !== sevFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const searchable = `${ev.event_type} ${ev.source_entity?.ip} ${ev.source_entity?.service} ${ev.destination_entity?.service} ${ev.mitre_technique}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });
  }, [events, search, layerFilter, sevFilter]);

  const exportCSV = () => {
    const header = 'timestamp,event_type,severity,source_ip,source_service,layer,mitre\n';
    const rows = filtered.map(ev =>
      `${ev.timestamp},${safeString(ev.event_type)},${getSeverityString(ev.severity)},${ev.source_entity?.ip},${ev.source_entity?.service},${safeString(ev.source_layer)},${safeString(ev.mitre_technique) || ''}`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `securisphere-events-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      <Card>
        {/* Toolbar */}
        <CardHeader className="flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <CardTitle>Security Events</CardTitle>
            <span className="text-[10px] font-mono text-base-500">{filtered.length} / {events.length}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-base-500" />
              <input
                type="text"
                placeholder="Search events..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="h-7 w-44 rounded-lg bg-white/[0.03] border border-white/[0.05] pl-8 pr-3 text-xs text-base-200 placeholder:text-base-500 outline-none focus:border-accent transition-all font-mono"
              />
            </div>
            <Select value={layerFilter} onChange={e => setLayerFilter(e.target.value)}>
              <option value="all">All Layers</option>
              <option value="network">Network</option>
              <option value="api">API</option>
              <option value="auth">Auth</option>
              <option value="browser">Browser</option>
            </Select>
            <Select value={sevFilter} onChange={e => setSevFilter(e.target.value)}>
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>
            <Button variant="secondary" size="sm" onClick={exportCSV}>
              <Download className="w-3 h-3" /> CSV
            </Button>
          </div>
        </CardHeader>

        {/* Table */}
        <div className="max-h-[70vh] overflow-y-auto">
          {filtered.length > 0 ? filtered.map((ev, i) => (
            <div key={ev.event_id || i}>
              <div
                onClick={() => setExpanded(expanded === ev.event_id ? null : ev.event_id)}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-white/[0.02] transition-colors',
                  i % 2 === 1 && 'bg-white/[0.01]',
                  i === 0 && 'animate-flash-row'
                )}
              >
                <div className="w-[3px] h-7 rounded shrink-0" style={{ background: severityColor(ev.severity) }} />
                {expanded === ev.event_id ? <ChevronDown className="w-3.5 h-3.5 text-base-500 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-base-500 shrink-0" />}
                <span className="text-xs font-medium text-base-200 flex-1 truncate">{safeString(ev.event_type)}</span>
                <Badge variant={getSeverityString(ev.severity)}>{getSeverityString(ev.severity)}</Badge>
                <span className="text-[11px] font-mono text-accent w-28 shrink-0 truncate">{ev.source_entity?.ip || ev.source_entity?.service}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-white/[0.05]" style={{ color: layerColor(safeString(ev.source_layer)) }}>
                  {safeString(ev.source_layer || 'N/A').toUpperCase()}
                </span>
                {ev.mitre_technique && (
                  <span className="text-[10px] font-mono text-accent bg-accent/[0.06] px-1.5 py-0.5 rounded">{ev.mitre_technique}</span>
                )}
                <span className="text-[10px] font-mono text-base-500 w-24 text-right shrink-0">{formatTimestampFull(ev.timestamp)}</span>
                <span className="text-[10px] font-mono text-base-600 w-8 text-right shrink-0">{ev.confidence || ''}</span>
              </div>

              <AnimatePresence>
                {expanded === ev.event_id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="overflow-hidden"
                  >
                    <pre className="mx-4 mb-3 p-3 rounded-lg bg-base-700/50 border border-white/[0.04] text-[11px] font-mono text-base-400 overflow-x-auto leading-relaxed">
                      {JSON.stringify(ev, null, 2)}
                    </pre>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )) : (
            <div className="py-16 text-center text-xs text-base-500">No events match filters</div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
