import { cn } from '@/lib/utils';

/**
 * Vertical band for a logical tier (Edge / App / Data).
 */
export default function LayerBlock({ title, subtitle, highlight, children, className }) {
  return (
    <section
      className={cn(
        'rounded-lg border border-dashed border-white/[0.08] bg-base-950/30 p-3',
        highlight && 'border-accent/25 bg-accent/[0.04]',
        className
      )}
    >
      <header className="mb-2.5 border-b border-dashed border-white/[0.06] pb-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-base-300">{title}</h3>
        {subtitle && <p className="mt-0.5 text-[10px] text-base-600">{subtitle}</p>}
      </header>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  );
}
