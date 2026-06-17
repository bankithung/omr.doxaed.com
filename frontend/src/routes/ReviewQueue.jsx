import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { listReview, resolveReview } from "@/api/scan"
import { Button } from "@/components/ui/button"

const OPTION_LABELS = ["A", "B", "C", "D", "E"]

const REASON_LABELS = {
  no_qr: "No QR code detected",
  alignment: "Alignment / fiducials not found",
  roll_unreadable: "Roll number unreadable",
  double_mark: "Double mark",
  faint: "Faint / ambiguous bubble",
  missing_page: "Missing page",
}

function ReasonBadge({ reason }) {
  return (
    <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
      {REASON_LABELS[reason] ?? reason}
    </span>
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

  return (
    <div className="rounded-xl border p-4">
      <div className="mb-3 flex flex-wrap items-start gap-2">
        <ReasonBadge reason={item.reason} />
        {item.sheet_code && (
          <span className="text-xs text-muted-foreground">Sheet: {item.sheet_code}</span>
        )}
        {item.omr_sheet && (
          <span className="text-xs text-muted-foreground">Sheet: {item.omr_sheet}</span>
        )}
        {(item.question || item.q_pos != null) && (
          <span className="text-xs text-muted-foreground">
            Q{item.q_pos ?? item.question}
          </span>
        )}
      </div>

      {/* Option selector — custom button group, no native select */}
      <div className="mb-4">
        <p className="mb-2 text-sm font-medium">Mark correct answer(s):</p>
        <div className="flex flex-wrap gap-2">
          {OPTION_LABELS.map((label) => (
            <button
              key={label}
              onClick={() => toggleOption(label)}
              className={`flex h-9 w-9 items-center justify-center rounded-lg border text-sm font-semibold transition-colors ${
                selected.includes(label)
                  ? "border-primary bg-primary text-primary-foreground"
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

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listReview(testId)
      setItems(data.results ?? data)
    } catch {
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
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Review queue</h1>
          <p className="text-sm text-muted-foreground">Test #{testId}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/results`}>Results</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/scan`}>Scan more</Link>
          </Button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading review items…</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl border p-8 text-center">
          <p className="text-muted-foreground">All items resolved — no pending reviews.</p>
          <Button asChild size="sm" className="mt-4" variant="outline">
            <Link to={`/tests/${testId}/results`}>View results</Link>
          </Button>
        </div>
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
    </div>
  )
}
