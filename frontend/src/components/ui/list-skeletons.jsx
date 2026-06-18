import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

/**
 * Content-shaped loading skeletons that mirror the real layouts used across the
 * app (DataList rows, detail headers, stat grids). Built on the base Skeleton so
 * spacing + the muted pulse stay consistent everywhere.
 */

/**
 * ListSkeleton — a stack of row placeholders matching a DataList / card list.
 *
 * Props:
 *   rows  — number of row placeholders (default 4)
 *   className — extra classes on the wrapper
 */
export function ListSkeleton({ rows = 4, className }) {
  return (
    <div className={cn("space-y-3", className)} aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-xl border px-4 py-3"
        >
          <Skeleton className="h-4 flex-1 max-w-[200px]" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="ml-auto h-9 w-16" />
        </div>
      ))}
    </div>
  )
}

/**
 * DetailHeaderSkeleton — a title + subtitle placeholder for detail pages.
 */
export function DetailHeaderSkeleton({ className }) {
  return (
    <div className={cn("space-y-3", className)} aria-hidden="true">
      <Skeleton className="h-7 w-48" />
      <Skeleton className="h-4 w-64" />
    </div>
  )
}

/**
 * TableSkeleton — a bordered block of equal-height row placeholders, for pages
 * that render a Table rather than a DataList.
 *
 * Props:
 *   rows  — number of placeholder rows (default 5)
 */
export function TableSkeleton({ rows = 5, className }) {
  return (
    <div className={cn("rounded-xl border", className)} aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "flex items-center gap-4 px-4 py-3",
            i !== rows - 1 && "border-b"
          )}
        >
          <Skeleton className="h-4 flex-1 max-w-[160px]" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="ml-auto h-4 w-20" />
        </div>
      ))}
    </div>
  )
}

/**
 * StatGridSkeleton — a row of stat-card placeholders.
 *
 * Props:
 *   count — number of cards (default 4)
 */
export function StatGridSkeleton({ count = 4, className }) {
  return (
    <div
      className={cn("grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4", className)}
      aria-hidden="true"
    >
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-20 rounded-xl" />
      ))}
    </div>
  )
}
