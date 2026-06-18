import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * StatCard — a compact metric card for dashboards.
 *
 * Props:
 *   label    — string  (required) — e.g. "Classes"
 *   value    — string | number | null | undefined
 *              undefined/null → skeleton loading state
 *              number → large tabular-nums display
 *              string → smaller, truncated
 *   sub      — ReactNode (optional) — small sub-text or link below the value
 *   loading  — boolean (optional) — force skeleton (overrides value check)
 *   className — extra classes on the card wrapper
 */
function StatCard({ label, value, sub, loading, className, ...props }) {
  const isLoading = loading || value === undefined || value === null
  const isNumber = !isLoading && typeof value === "number"

  return (
    <div
      data-slot="stat-card"
      className={cn(
        "flex min-w-0 flex-col gap-1 rounded-lg border border-border bg-card p-4",
        className
      )}
      {...props}
    >
      <span className="truncate text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>

      {isLoading ? (
        <Skeleton className="my-1 h-6 w-14" />
      ) : (
        <span
          className={cn(
            "font-bold text-foreground",
            isNumber ? "tabular text-2xl" : "truncate text-sm"
          )}
          title={isNumber ? undefined : String(value)}
        >
          {value}
        </span>
      )}

      {sub && (
        <span className="truncate text-xs text-muted-foreground">{sub}</span>
      )}
    </div>
  )
}

export { StatCard }
