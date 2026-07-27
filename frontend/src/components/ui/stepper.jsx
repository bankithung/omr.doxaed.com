import { cn } from "@/lib/utils"

/**
 * StepperCompact — a space-saving "Step N of M" + dots indicator for narrow
 * viewports. Pair with the full <Stepper> (show one or the other per breakpoint).
 */
export function StepperCompact({ steps, current = 0, className }) {
  const total = steps.length
  const label = steps[current] ?? ""
  return (
    <div className={cn("flex items-center justify-between gap-3", className)}>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Step {current + 1} of {total}
        </p>
        <p className="truncate text-sm font-semibold">{label}</p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5" aria-hidden="true">
        {steps.map((s, i) => (
          <span
            key={s}
            className={cn(
              "h-2 rounded-full transition-all",
              i === current ? "w-5 bg-primary" : i < current ? "w-2 bg-indigo/50" : "w-2 bg-muted-foreground/30",
            )}
          />
        ))}
      </div>
    </div>
  )
}

export function Stepper({ steps, current = 0, className }) {
  return (
    <ol className={cn("flex items-center gap-4", className)}>
      {steps.map((label, i) => {
        const state = i < current ? "done" : i === current ? "active" : "todo"
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium",
                state === "done" && "bg-primary text-primary-foreground",
                state === "active" && "border-2 border-indigo text-indigo",
                state === "todo" && "border border-muted-foreground/40 text-muted-foreground",
              )}
            >
              {i + 1}
            </span>
            <span className={cn("text-sm", state === "todo" && "text-muted-foreground")}>
              {label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
