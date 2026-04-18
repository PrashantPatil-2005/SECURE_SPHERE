import { cn } from '@/lib/utils';

/**
 * Reusable bordered card for intro sections.
 */
export default function SectionCard({ title, description, children, className }) {
  return (
    <section
      className={cn(
        'rounded-lg border border-base-800 bg-base-900/80 p-4 shadow-none',
        className
      )}
    >
      {title && (
        <header className="mb-3 border-b border-base-800 pb-2">
          <h2 className="text-sm font-semibold tracking-tight text-base-100">{title}</h2>
          {description && <p className="mt-1 text-xs leading-relaxed text-base-500">{description}</p>}
        </header>
      )}
      <div className="text-sm leading-relaxed text-base-300">{children}</div>
    </section>
  );
}
