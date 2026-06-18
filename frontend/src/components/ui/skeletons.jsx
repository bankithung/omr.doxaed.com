import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

/**
 * Skeleton kit (App-shell v2) — flat, token-driven placeholders whose heights
 * match the real surfaces so swapping them in causes zero layout shift.
 * All respect prefers-reduced-motion via `motion-reduce:animate-none`.
 *
 * Coexists with the legacy `list-skeletons.jsx`; prefer these for new surfaces.
 */

const pulse = "motion-reduce:animate-none"

/** StatCardSkeleton — single dashboard metric card placeholder. */
export function StatCardSkeleton({ className }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "flex min-w-0 flex-col gap-2 rounded-lg border border-border bg-card p-4",
        className
      )}
    >
      <Skeleton className={cn("h-3 w-16", pulse)} />
      <Skeleton className={cn("h-7 w-12", pulse)} />
    </div>
  )
}

/** CardGridSkeleton — a responsive grid of StatCardSkeletons. */
export function CardGridSkeleton({ count = 4, className }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4",
        className
      )}
    >
      {Array.from({ length: count }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  )
}

/** ListRowSkeleton — one 44px DataTable/list row placeholder. */
export function ListRowSkeleton({ className }) {
  return (
    <div
      aria-hidden="true"
      className={cn("flex h-11 items-center gap-3 px-3", className)}
    >
      <Skeleton className={cn("h-4 max-w-[200px] flex-1", pulse)} />
      <Skeleton className={cn("h-4 w-20", pulse)} />
      <Skeleton className={cn("ml-auto h-4 w-10", pulse)} />
    </div>
  )
}

/**
 * TableSkeleton — bordered block of 44px rows under a muted header strip,
 * matching the DataTable layout exactly.
 */
export function TableSkeleton({ rows = 6, className }) {
  return (
    <div
      aria-hidden="true"
      className={cn("overflow-hidden rounded-lg border border-border", className)}
    >
      <div className="flex h-9 items-center gap-3 border-b border-border bg-surface-1 px-3">
        <Skeleton className={cn("h-3 w-24", pulse)} />
        <Skeleton className={cn("ml-auto h-3 w-16", pulse)} />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "flex h-11 items-center gap-3 px-3",
            i !== rows - 1 && "border-b border-border"
          )}
        >
          <Skeleton className={cn("h-4 max-w-[180px] flex-1", pulse)} />
          <Skeleton className={cn("h-4 w-24", pulse)} />
          <Skeleton className={cn("ml-auto h-4 w-10", pulse)} />
        </div>
      ))}
    </div>
  )
}
