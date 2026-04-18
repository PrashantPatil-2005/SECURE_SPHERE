import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from 'recharts';

const COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-base-800 bg-base-800/95 backdrop-blur-sm px-3 py-2 shadow-lg">
      <div className="text-[10px] text-base-500 font-mono mb-1">{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-base-300 capitalize">{p.dataKey}</span>
          <span className="font-mono font-semibold text-base-100 ml-auto">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function EventsAreaChart({ data = [] }) {
  const formatted = data.map((d, i) => ({
    name: new Date(d.timestamp).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' }),
    critical: d.critical || 0,
    high: d.high || 0,
    medium: d.medium || 0,
    low: d.low || 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={formatted} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
        <defs>
          {Object.entries(COLORS).map(([key, color]) => (
            <linearGradient key={key} id={`area-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.2} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#64748b' }} stroke="transparent" />
        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} stroke="transparent" allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />
        {Object.entries(COLORS).map(([key, color]) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#area-${key})`}
            stackId="1"
            dot={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
