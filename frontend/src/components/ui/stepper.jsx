import { cn } from "@/lib/utils"

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
                state === "active" && "border-2 border-primary text-primary",
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
