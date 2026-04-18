import { motion } from 'framer-motion';
import { Crosshair, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const anim = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.2 } };

/**
 * MITRE ATT&CK coverage placeholder — extend with tactic/technique matrix + detections.
 */
export default function Mitre() {
  return (
    <motion.div {...anim} className="mx-auto flex max-w-4xl flex-col gap-4">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-base-100">MITRE ATT&CK</h2>
        <p className="mt-1 max-w-2xl text-sm text-base-500">
          Map container and cloud detections to tactics and techniques. Wire telemetry and kill-chain
          stages here for coverage gaps and purple-team planning.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center gap-2 border-b border-dashed border-white/[0.06]">
          <Crosshair className="h-4 w-4 text-accent" />
          <CardTitle className="text-sm">Coverage matrix</CardTitle>
        </CardHeader>
        <CardContent className="py-10 text-center">
          <p className="font-mono text-xs text-base-500">
            Matrix and technique drill-downs will render from correlation + narration metadata.
          </p>
          <a
            href="https://attack.mitre.org/matrices/enterprise/containers/"
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:underline"
          >
            MITRE ATT&CK for Containers
            <ExternalLink className="h-3 w-3" />
          </a>
        </CardContent>
      </Card>
    </motion.div>
  );
}
