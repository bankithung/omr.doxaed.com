import { cn } from "@/lib/utils"

/**
 * PageShell — the shared page rhythm wrapper for every route.
 *
 * Matches fet's `.page`: 90% of the available width, capped at 1600px, centred,
 * with responsive padding and a soft rise on mount. The width steps up on
 * smaller screens (94% tablet, 96% phone, 100% small phone) so narrow viewports
 * do not waste their margins.
 *
 * Props:
 *   children  — page content
 *   className — extra classes
 */
function PageShell({ children, className, ...props }) {
  return (
    <div
      data-slot="page-shell"
      className={cn(
        /* px matches the `-mx-4` / `sm:-mx-6` full bleed rows (sticky action
           bars, scroll rails) so they sit flush instead of overflowing */
        "page-width fet-rise space-y-6 px-4 py-4 sm:px-6 md:space-y-8 md:py-6",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export { PageShell }
