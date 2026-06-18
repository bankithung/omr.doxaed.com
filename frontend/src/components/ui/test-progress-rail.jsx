import { Link } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * TestProgressRail — a horizontal, scroll-on-mobile rail of the test lifecycle
 * stages (Build → Generate → Scan → Review → Results → Analytics).
 *
 * Replaces the old per-page "sibling button row". Each stage links to the SAME
 * destination the buttons used to point at — the routes are unchanged so the
 * frozen E2E (which hits `/tests/:id/<route>` by URL) keeps working:
 *
 *   Build     → /classes/:classId               (test list / wizard entry)
 *   Generate  → /classes/:classId               (Generate sheets dialog lives here)
 *   Scan      → /tests/:testId/scan
 *   Review    → /tests/:testId/review
 *   Results   → /tests/:testId/results
 *   Analytics → /tests/:testId/analytics
 *
 * Props:
 *   testId   — string|number (required) — used for the test-scoped routes
 *   classId  — string|number (optional) — used for Build/Generate; when absent
 *              those stages render as non-links (still visible for context).
 *   current  — one of "build"|"generate"|"scan"|"review"|"results"|"analytics"
 *   className
 */

const STAGES = [
  { key: "build", label: "Build" },
  { key: "generate", label: "Generate" },
  { key: "scan", label: "Scan" },
  { key: "review", label: "Review" },
  { key: "results", label: "Results" },
  { key: "analytics", label: "Analytics" },
]

function stageHref({ key, testId, classId }) {
  switch (key) {
    case "build":
    case "generate":
      return classId != null ? `/classes/${classId}` : null
    case "scan":
      return `/tests/${testId}/scan`
    case "review":
      return `/tests/${testId}/review`
    case "results":
      return `/tests/${testId}/results`
    case "analytics":
      return `/tests/${testId}/analytics`
    default:
      return null
  }
}

function TestProgressRail({ testId, classId, current, className }) {
  const currentIdx = STAGES.findIndex((s) => s.key === current)

  return (
    <nav
      aria-label="Test progress"
      data-slot="test-progress-rail"
      className={cn(
        // Horizontal scroll on mobile; no wrap so stages stay on one row.
        "-mx-4 overflow-x-auto px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
        className
      )}
    >
      <ol className="flex w-max min-w-full items-center gap-1 rounded-xl border bg-card p-1 shadow-sm">
        {STAGES.map((stage, idx) => {
          const href = stageHref({ key: stage.key, testId, classId })
          const isCurrent = stage.key === current
          const isDone = currentIdx >= 0 && idx < currentIdx

          const content = (
            <span
              className={cn(
                "flex min-h-[40px] items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                isCurrent
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                  isCurrent
                    ? "bg-primary-foreground/20 text-primary-foreground"
                    : isDone
                    ? "bg-primary/15 text-primary"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {idx + 1}
              </span>
              {stage.label}
            </span>
          )

          return (
            <li key={stage.key} className="flex shrink-0 items-center">
              {href && !isCurrent ? (
                <Link
                  to={href}
                  aria-current={undefined}
                  className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                >
                  {content}
                </Link>
              ) : (
                <span aria-current={isCurrent ? "step" : undefined}>{content}</span>
              )}
              {idx < STAGES.length - 1 && (
                <ChevronRight
                  className="size-3.5 shrink-0 text-muted-foreground/40"
                  aria-hidden="true"
                />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export { TestProgressRail }
