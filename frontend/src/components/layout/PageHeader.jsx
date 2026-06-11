import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function PageHeader({
  title,
  description,
  breadcrumbs,
  icon: Icon,
  actions,
  className,
}) {
  return (
    <div className={cn('mb-6 flex flex-col gap-2', className)}>
      {breadcrumbs?.length ? (
        <nav className="flex items-center gap-1 type-caption" aria-label="Breadcrumb">
          {breadcrumbs.map((b, i) => (
            <span key={`${b.label}-${i}`} className="inline-flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3 shrink-0 text-base-700" />}
              {b.href ? (
                <a href={b.href} className="transition-colors hover:text-base-300">{b.label}</a>
              ) : (
                <span className={cn(i === breadcrumbs.length - 1 && 'font-medium text-base-300')}>
                  {b.label}
                </span>
              )}
            </span>
          ))}
        </nav>
      ) : null}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            {Icon && (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-base-800 bg-base-900">
                <Icon className="h-4 w-4 text-accent" />
              </div>
            )}
            <h1 className="type-page-title truncate">{title}</h1>
          </div>
          {description && (
            <p className="type-caption mt-1.5 max-w-2xl">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
