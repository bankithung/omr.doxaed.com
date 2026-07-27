import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { CheckCircleIcon } from "lucide-react"
import { listReview, resolveReview } from "@/api/scan"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/skeletons"

const OPTION_LABELS = ["A", "B", "C", "D", "E"]

const REASON_LABELS = {
  no_qr: "No QR code detected",
  alignment: "Alignment / fiducials not found",
  roll_unreadable: "Roll number unreadable",
  double_mark: "Double mark",
  faint: "Faint / ambiguous bubble",
  missing_page: "Missing page",
  // Phase 1B — scan identity + roll reconciliation
  test_mismatch: "Wrong test, sheet belongs to a different test",
  roll_mismatch: "Roll number mismatch, verify student identity",
}

// Reasons that are about the whole sheet, not one answer. There is no single
// response to correct, so offering an A to E picker on these was an action that
// could never succeed.
const SHEET_LEVEL_REASONS = new Set([
  "no_qr",
  "alignment",
  "roll_unreadable",
  "roll_mismatch",
  "missing_page",
  "test_mismatch",
])

// What the teacher should actually do about a sheet-level flag.
const SHEET_LEVEL_GUIDANCE = {
  no_qr: "The QR code could not be read. Re-photograph the sheet with the whole page in frame, then upload it again.",
  alignment:
    "The four corner squares could not be found. Photograph the sheet flat on a plain light surface with all four corners inside the frame, then upload it again.",
  roll_unreadable:
    "The roll number grid could not be read. Open the sheet in Results and set the student by hand, or re-scan a cleaner photo.",
  roll_mismatch:
    "The bubbled roll number does not match the student this sheet was printed for. Confirm who sat this paper before trusting the score.",
  missing_page:
    "At least one page of this sheet has not been scanned yet. Upload the remaining pages.",
  test_mismatch:
    "This sheet was printed for a different exam. Upload it to that exam instead.",
}

function ReasonBadge({ reason }) {
  return (
    <Badge variant="error">{REASON_LABELS[reason] ?? reason}</Badge>
  )
}

function ReviewItemCard({ item, onResolved }) {
  const [selected, setSelected] = useState([])
  const [resolving, setResolving] = useState(false)

  function toggleOption(label) {
    setSelected((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label]
    )
  }

  async function handleResolve() {
    if (selected.length === 0) {
      toast.error("Select at least one option to mark as correct")
      return
    }
    setResolving(true)
    try {
      await resolveReview(item.id, selected)
      toast.success(`Item #${item.id} resolved`)
      onResolved(item.id)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        "Failed to resolve"
      toast.error(msg)
    } finally {
      setResolving(false)
    }
  }

  const sheetLevel = SHEET_LEVEL_REASONS.has(item.reason) || item.q_pos == null

  const header = (
    <div className="mb-3 flex flex-wrap items-start gap-2">
      <ReasonBadge reason={item.reason} />
      {item.sheet_code && (
        <span className="text-xs text-muted-foreground">Sheet: {item.sheet_code}</span>
      )}
      {!item.sheet_code && item.omr_sheet && (
        <span className="text-xs text-muted-foreground">Sheet: {item.omr_sheet}</span>
      )}
      {item.q_pos != null && (
        <span className="text-xs font-semibold text-foreground">
          Question {item.q_pos}
        </span>
      )}
    </div>
  )

  // Sheet-level flags get an informational card with the one real next step.
  // Older items carry no q_pos, so they land here too rather than offering a
  // picker whose answer would be applied to the wrong question.
  if (sheetLevel) {
    return (
      <div className="rounded-lg border border-border p-4">
        {header}
        <p className="text-sm text-[var(--text-soft)]">
          {SHEET_LEVEL_GUIDANCE[item.reason] ??
            "This flag is about the whole sheet, not one answer. Re-scan the sheet to clear it."}
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border p-4">
      {header}

      {/* Option selector — custom button group, no native select */}
      <div className="mb-4">
        <p className="mb-2 text-sm font-medium">
          Mark the correct answer for question {item.q_pos}:
        </p>
        <div className="flex flex-wrap gap-2">
          {OPTION_LABELS.map((label) => (
            <button
              key={label}
              type="button"
              aria-pressed={selected.includes(label)}
              onClick={() => toggleOption(label)}
              className={`flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg border text-sm font-semibold transition-colors ${
                selected.includes(label)
                  ? "border-indigo bg-primary text-primary-foreground"
                  : "border-input bg-transparent text-foreground hover:bg-muted"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {selected.length > 0 && (
          <p className="mt-1.5 text-xs text-muted-foreground">
            Selected: {selected.join(", ")}
          </p>
        )}
      </div>

      <Button
        size="sm"
        onClick={handleResolve}
        disabled={resolving || selected.length === 0}
      >
        {resolving ? "Resolving…" : "Resolve"}
      </Button>
    </div>
  )
}

export default function ReviewQueue() {
  const { testId } = useParams()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchItems = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await listReview(testId)
      setItems(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load review queue")
    } finally {
      setLoading(false)
    }
  }, [testId])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  function handleResolved(id) {
    setItems((prev) => prev.filter((item) => item.id !== id))
  }

  return (
 <PageShell className="">
      <PageHeader
        title="Review queue"
        description={`Test #${testId}`}
      />

      {loading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState
          title="Couldn't load review queue"
          description="Something went wrong while loading items pending review."
          onRetry={fetchItems}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={CheckCircleIcon}
          title="All caught up"
          description="All items resolved, no pending reviews."
          action={
            <Button asChild variant="outline">
              <Link to={`/tests/${testId}/results`}>View results</Link>
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            {items.length} item{items.length !== 1 ? "s" : ""} pending review
          </p>
          {items.map((item) => (
            <ReviewItemCard key={item.id} item={item} onResolved={handleResolved} />
          ))}
        </div>
      )}
    </PageShell>
  )
}
