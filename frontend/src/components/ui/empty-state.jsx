import { cn } from "@/lib/utils"

/**
 * EmptyState — centered icon + title + one-line guidance + a single primary action.
 *
 * Props:
 *   icon        — optional lucide icon component (e.g. FolderIcon). Rendered in a
 *                 muted circle above the title. Pass the component, not an element.
 *   title       — string | ReactNode (required)
 *   description — string | ReactNode (optional one-line guidance)
 *   action      — ReactNode rendered below the description (optional single action)
 *   className   — extra classes on the wrapper
 */
export function EmptyState({ icon: Icon, title, description, action, className }) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 p-10 text-center", className)}>
      {Icon && (
        <div className="mb-1 flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Icon className="size-6" aria-hidden="true" />
        </div>
      )}
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
