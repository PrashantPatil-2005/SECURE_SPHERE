import { useState } from 'react';
import { motion } from 'framer-motion';
import { Network, Info } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Select } from '@/components/ui/input';
import TopologyGraph from '@/components/TopologyGraph';
import TopologyChecklist from '@/components/TopologyChecklist';
import { threatLevelColor } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

const LEGEND = [
  { label: 'Normal', level: 'normal' },
  { label: 'Suspicious', level: 'suspicious' },
  { label: 'Threatening', level: 'threatening' },
  { label: 'Critical', level: 'critical' },
];

export default function Topology({ topology, riskScores, incidents }) {
  const [selectedIncident, setSelectedIncident] = useState('none');

  const attackPath = selectedIncident !== 'none'
    ? incidents.find(i => i.incident_id === selectedIncident)?.service_path || []
    : [];

  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-base-100 tracking-tight">Service Topology</h2>
          <span className="text-xs font-mono text-base-500">
            {topology.nodes?.length || 0} nodes, {topology.edges?.length || 0} edges
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-base-500">Overlay attack path:</span>
          <Select value={selectedIncident} onChange={e => setSelectedIncident(e.target.value)}>
            <option value="none">None</option>
            {incidents.map(inc => (
              <option key={inc.incident_id} value={inc.incident_id}>
                {inc.title?.slice(0, 40) || inc.incident_id}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_200px] gap-4">
        <Card className="overflow-hidden p-0">
          {topology.nodes?.length > 0 ? (
            <TopologyGraph
              topology={topology}
              riskScores={riskScores}
              height={520}
              attackPath={attackPath}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-[520px] text-base-500 text-sm gap-3">
              <Network className="w-10 h-10 opacity-20" />
              <span>No topology data available</span>
              <span className="text-xs text-base-600">Start the backend to see the service graph</span>
            </div>
          )}
        </Card>

        {/* Right column */}
        <div className="flex flex-col gap-3">
          <TopologyChecklist />
          <Card>
            <CardHeader>
              <CardTitle>Legend</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2.5">
              {LEGEND.map(l => (
                <div key={l.level} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border-2" style={{ borderColor: threatLevelColor(l.level), background: `${threatLevelColor(l.level)}22` }} />
                  <span className="text-xs text-base-300">{l.label}</span>
                </div>
              ))}
              <div className="h-px bg-white/[0.05] my-1" />
              <div className="flex items-center gap-2">
                <div className="w-6 h-0 border-t-2 border-dashed border-red-500" />
                <span className="text-xs text-base-300">Attack path</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0 border-t border-white/10" />
                <span className="text-xs text-base-300">Dependency</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Info</CardTitle>
              <Info className="w-3.5 h-3.5 text-base-500" />
            </CardHeader>
            <CardContent className="text-[11px] text-base-400 leading-relaxed">
              Drag nodes to rearrange. Scroll to zoom. Select an incident above to overlay its attack traversal path.
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  );
}
