import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { layerColor } from '@/lib/utils';

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="rounded-lg border border-base-800 bg-base-800/95 backdrop-blur-sm px-3 py-2 shadow-lg">
      <div className="flex items-center gap-2 text-xs">
        <div className="w-2 h-2 rounded-full" style={{ background: d.payload.fill }} />
        <span className="text-base-200 capitalize">{d.name}</span>
        <span className="font-mono font-semibold text-base-100 ml-2">{d.value}</span>
      </div>
    </div>
  );
}

export default function ThreatDonutChart({ events = [] }) {
  const counts = { network: 0, api: 0, auth: 0, browser: 0 };
  events.forEach(ev => {
    const layer = ev.source_layer?.toLowerCase();
    if (layer && counts[layer] !== undefined) counts[layer]++;
  });

  const data = Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value, fill: layerColor(name) }));

  if (data.length === 0) {
    data.push({ name: 'No data', value: 1, fill: '#1a2235' });
  }

  return (
    <div className="flex items-center gap-4">
      <ResponsiveContainer width={140} height={140}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={60}
            paddingAngle={3}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-col gap-2">
        {Object.entries(counts).map(([layer, count]) => (
          <div key={layer} className="flex items-center gap-2 text-xs">
            <div className="w-2 h-2 rounded-full" style={{ background: layerColor(layer) }} />
            <span className="text-base-400 capitalize w-14">{layer}</span>
            <span className="font-mono font-semibold text-base-200">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
