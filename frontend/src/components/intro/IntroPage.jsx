import { motion } from 'framer-motion';
import PageHeader from '@/components/intro/PageHeader';
import SectionCard from '@/components/intro/SectionCard';
import KillChainFlow from '@/components/intro/KillChainFlow';
import DesignSystem from '@/components/intro/DesignSystem';
import DocGuide from '@/components/intro/DocGuide';

const anim = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.2 } };

/**
 * Onboarding / overview — wireframe content as production JSX (no innerHTML).
 */
export default function IntroPage() {
  return (
    <motion.div {...anim} className="mx-auto max-w-5xl space-y-6 text-base-200">
      <PageHeader />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionCard
          title="What we’re designing for"
          description="Operator-first layout for detect → investigate → respond."
        >
          <p className="mb-4 text-sm leading-relaxed text-base-400">
            SecuriSphere correlates east–west movement between named services and reconstructs kill chains on a live
            dependency graph. These screens define the operator console: navigation shells, topology, and incident
            workflow — clarity and scanability over ornamental chrome. Use the sidebar or press{' '}
            <kbd className="rounded border border-base-800 px-1 font-mono text-xs">2</kbd> for Dashboard,{' '}
            <kbd className="rounded border border-base-800 px-1 font-mono text-xs">t</kbd> for tweaks.
          </p>
          <KillChainFlow />
        </SectionCard>

        <SectionCard title="Design system" description="Typography, severity, and primitives.">
          <DesignSystem />
        </SectionCard>
      </div>

      <SectionCard title="How to read this document" description="Conventions used across wireframes.">
        <DocGuide />
      </SectionCard>
    </motion.div>
  );
}
