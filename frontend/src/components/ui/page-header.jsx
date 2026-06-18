import { cn } from "@/lib/utils"

/**
 * PageHeader — title + optional description + right-aligned actions slot,
 * plus optional breadcrumb (above the title) and tabs (below the header) slots.
 *
 * Props:
 *   title       — string | ReactNode (required)
 *   description — string | ReactNode (optional)
 *   actions     — ReactNode rendered right-aligned (optional)
 *   breadcrumb  — ReactNode rendered above the title (optional)
 *   tabs        — ReactNode rendered below the header row (optional, e.g. a TabsList)
 *   className   — extra classes on the wrapper
 */
function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
  tabs,
  className,
  ...props
}) {
  return (
    <div
      data-slot="page-header"
      className={cn("flex flex-col gap-3", className)}
      {...props}
    >
      {breadcrumb && <div className="min-w-0">{breadcrumb}</div>}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-heading text-2xl font-bold leading-tight tracking-tight text-foreground">
            {title}
          </h1>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        )}
      </div>
      {tabs && <div className="min-w-0">{tabs}</div>}
    </div>
  )
}

export { PageHeader }
