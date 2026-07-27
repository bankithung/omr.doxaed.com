import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

/* fet's .badge: an 11px uppercase chip on the tray surface with a hairline
   border and 5px corners. Status variants tint the same shape. */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 text-xs font-semibold tracking-[0.5px] uppercase",
  {
    variants: {
      variant: {
        success:
          "border-[var(--color-success)]/45 bg-[var(--color-success)]/[0.10] text-[var(--color-success)]",
        warning:
          "border-[var(--color-warning)]/45 bg-[var(--color-warning)]/[0.14] text-[var(--color-warning)]",
        error:
          "border-destructive/50 bg-destructive/[0.10] text-destructive",
        info:
          "border-[var(--accent-solid)]/45 bg-[var(--accent-solid)]/[0.09] text-[var(--accent-solid)]",
        neutral:
          "border-border bg-secondary text-muted-foreground",
        // brand / live — pairs with StatusDot for live status
        brand:
          "border-primary bg-primary text-primary-foreground",
        default:
          "border-primary bg-primary text-primary-foreground",
        secondary:
          "border-border bg-secondary text-secondary-foreground",
        destructive:
          "border-destructive/50 bg-destructive/[0.10] text-destructive",
        outline:
          "border-border bg-transparent text-foreground",
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

// Map a semantic status → the status token used for the dot fill.
const STATUS_DOT_COLOR = {
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  error: "var(--color-error)",
  info: "var(--color-info)",
  neutral: "var(--muted-foreground)",
}

/**
 * StatusDot — a tiny colored dot + label for DENSE table cells (where a pill
 * Badge would be too heavy). Use Badge in cards/headers, StatusDot in rows.
 *
 * Props:
 *   status — one of "success" | "warning" | "error" | "info" | "neutral"
 *   children — the label text
 */
function StatusDot({ status = "neutral", className, children, ...props }) {
  return (
    <span
      data-slot="status-dot"
      className={cn("inline-flex items-center gap-1.5 text-sm", className)}
      {...props}
    >
      <span
        aria-hidden="true"
        className="size-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: STATUS_DOT_COLOR[status] ?? STATUS_DOT_COLOR.neutral }}
      />
      {children}
    </span>
  )
}

export { Badge, badgeVariants, StatusDot }
