import { cn } from "@/lib/utils"

export function EmptyState({ title, description, action, className }) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 p-10 text-center", className)}>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
