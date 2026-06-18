import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        // semantic variants mapped to theme tokens
        success:
          "bg-[color-mix(in_oklch,var(--color-success)_15%,transparent)] text-[var(--color-success)] dark:bg-[color-mix(in_oklch,var(--color-success)_20%,transparent)]",
        warning:
          "bg-[color-mix(in_oklch,var(--color-warning)_15%,transparent)] text-[var(--color-warning)] dark:bg-[color-mix(in_oklch,var(--color-warning)_20%,transparent)]",
        error:
          "bg-[color-mix(in_oklch,var(--color-error)_12%,transparent)] text-[var(--color-error)] dark:bg-[color-mix(in_oklch,var(--color-error)_20%,transparent)]",
        info:
          "bg-[color-mix(in_oklch,var(--color-info)_12%,transparent)] text-[var(--color-info)] dark:bg-[color-mix(in_oklch,var(--color-info)_20%,transparent)]",
        neutral:
          "bg-muted text-muted-foreground",
        // shadcn-compatible default
        default:
          "border border-transparent bg-primary text-primary-foreground",
        secondary:
          "border border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border border-transparent bg-destructive text-white",
        outline:
          "border border-border text-foreground",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
)

function Badge({ className, variant, ...props }) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
