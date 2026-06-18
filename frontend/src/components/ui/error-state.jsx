import { AlertTriangleIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

/**
 * ErrorState — a consistent inline fetch-error panel with a retry action.
 *
 * Use this instead of leaving a blank page when a route's main data fetch fails.
 * Pairs with a `useState(error)` flag set in the fetch's catch block; `onRetry`
 * should re-run that same fetch.
 *
 * Props:
 *   title       — short headline (default "Couldn't load this")
 *   description — optional detail line (e.g. the backend message)
 *   onRetry     — handler for the "Try again" button (button hidden if omitted)
 *   retryLabel  — override the retry button label (default "Try again")
 *   className   — extra classes on the wrapper
 */
export function ErrorState({
  title = "Couldn't load this",
  description,
  onRetry,
  retryLabel = "Try again",
  className,
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border p-10 text-center",
        className
      )}
    >
      <div className="mb-1 flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangleIcon className="size-6" aria-hidden="true" />
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && (
        <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-2 min-h-[40px]">
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
