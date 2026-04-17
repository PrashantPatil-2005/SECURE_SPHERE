import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/Badge';
import RiskGauge from '@/components/charts/RiskGauge';
import SparkLine from '@/components/charts/SparkLine';
import { cn, threatLevelColor } from '@/lib/utils';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } };

export default function RiskScores({ riskScores }) {
  const entries = Object.entries(riskScores || {}).filter(([, v]) => v);

  // Generate synthetic sparkline data per service
  const sparkData = (score) => Array.from({ length: 15 }, (_, i) => ({
    value: Math.max(0, score + Math.floor((Math.random() - 0.5) * 20)),
  }));

  return (
    <motion.div {...anim} className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-bold text-base-100 tracking-tight">Risk Scores</h2>
        <span className="text-xs font-mono text-base-500">{entries.length} services monitored</span>
      </div>

      {entries.length > 0 ? (
        <div className="grid grid-cols-3 gap-4">
          {entries.map(([service, data]) => {
            const score = data?.current_score || 0;
            const level = data?.threat_level?.toLowerCase() || 'normal';
            const color = threatLevelColor(level);
            const levelLabel = level.charAt(0).toUpperCase() + level.slice(1);
            const status = data?.status || 'active';

            return (
              <Card key={service} className={cn(
                'overflow-hidden transition-colors',
                score > 150 && 'border-severity-critical/40'
              )}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-sm font-semibold text-base-100 mb-1">{service}</h3>
                      <Badge variant={status === 'active' ? 'low' : status === 'degraded' ? 'medium' : 'critical'}>
                        {status}
                      </Badge>
                    </div>
                    <RiskGauge score={score} level={level} size={72} />
                  </div>

                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs font-semibold" style={{ color }}>{levelLabel}</span>
                    <span className="text-[10px] font-mono text-base-500">Score: {score}/200</span>
                  </div>

                  {/* Mini sparkline */}
                  <div className="mb-3">
                    <SparkLine data={sparkData(score)} color={color} height={28} />
                  </div>

                  {/* Top contributing events */}
                  {data?.top_events?.length > 0 && (
                    <div>
                      <div className="text-[10px] text-base-500 mb-1 uppercase tracking-wider font-semibold">Top Events</div>
                      {data.top_events.slice(0, 3).map((evt, i) => (
                        <div key={i} className="text-[11px] text-base-400 truncate py-0.5">
                          &bull; {evt}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="py-16 text-center">
            <Zap className="w-8 h-8 mx-auto mb-3 text-base-500 opacity-30" />
            <p className="text-sm text-base-500">No risk data available</p>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
