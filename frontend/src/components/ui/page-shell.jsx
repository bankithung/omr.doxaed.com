import { cn } from "@/lib/utils"

/**
 * PageShell — the shared page rhythm wrapper for every authenticated route.
 *
 * Centers content, applies the standard max-width (max-w-5xl), vertical rhythm
 * (space-y-8) and responsive padding (p-6 md:p-8). Workbench / data-heavy pages
 * can widen by passing a different max-width via `className` (e.g. "max-w-6xl"),
 * which overrides the default thanks to tailwind-merge.
 *
 * Props:
 *   children  — page content
 *   className — extra classes (e.g. a wider max-width for workbench pages)
 */
function PageShell({ children, className, ...props }) {
  return (
    <div
      data-slot="page-shell"
      className={cn("mx-auto max-w-5xl space-y-8 p-6 md:p-8", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export { PageShell }
