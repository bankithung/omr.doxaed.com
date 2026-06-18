import { cn } from "@/lib/utils"

/**
 * PageHeader — title + optional description + right-aligned actions slot.
 *
 * Props:
 *   title       — string | ReactNode (required)
 *   description — string | ReactNode (optional)
 *   actions     — ReactNode rendered right-aligned (optional)
 *   className   — extra classes on the wrapper
 */
function PageHeader({ title, description, actions, className, ...props }) {
  return (
    <div
      data-slot="page-header"
      className={cn(
        "flex flex-wrap items-start justify-between gap-4",
        className
      )}
      {...props}
    >
      <div className="min-w-0 flex-1">
        <h1 className="font-heading text-2xl font-bold leading-tight tracking-tight text-foreground truncate">
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
  )
}

export { PageHeader }
