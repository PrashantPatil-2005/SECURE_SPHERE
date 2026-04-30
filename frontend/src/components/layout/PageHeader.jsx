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
    <div className={cn('mb-5 flex flex-col gap-2', className)}>
      {breadcrumbs?.length ? (
        <nav className="flex items-center gap-1 text-[11px] text-base-500" aria-label="Breadcrumb">
          {breadcrumbs.map((b, i) => (
            <span key={`${b.label}-${i}`} className="inline-flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3 text-base-700" />}
              {b.href ? (
                <a href={b.href} className="hover:text-base-300 transition-colors">{b.label}</a>
              ) : (
                <span className={cn(i === breadcrumbs.length - 1 && 'text-base-300')}>{b.label}</span>
              )}
            </span>
          ))}
        </nav>
      ) : null}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            {Icon && (
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-base-800 bg-base-900">
                <Icon className="h-4 w-4 text-base-300" />
              </div>
            )}
            <h1 className="truncate text-lg font-semibold tracking-tight text-base-100">{title}</h1>
          </div>
          {description && (
            <p className="mt-1 text-xs text-base-500">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
