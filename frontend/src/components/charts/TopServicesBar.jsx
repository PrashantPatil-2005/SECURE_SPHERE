import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { severityColor } from '@/lib/utils';

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="rounded-lg border border-white/10 bg-base-800/95 backdrop-blur-sm px-3 py-2 shadow-lg text-xs">
      <span className="text-base-200">{d.payload.name}</span>
      <span className="font-mono font-semibold text-base-100 ml-2">{d.value}</span>
    </div>
  );
}

export default function TopServicesBar({ events = [] }) {
  const counts = {};
  events.forEach(ev => {
    const svc = ev.destination_entity?.service || ev.source_entity?.service;
    if (svc) counts[svc] = (counts[svc] || 0) + 1;
  });

  const data = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6)
    .map(([name, count]) => ({ name: name.replace('-service', ''), count }));

  if (data.length === 0) return <div className="text-center text-base-500 text-xs py-8">No service data</div>;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 5, bottom: 0, left: 0 }}>
        <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} stroke="transparent" />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="transparent" width={80} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
        <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={16} />
      </BarChart>
    </ResponsiveContainer>
  );
}
