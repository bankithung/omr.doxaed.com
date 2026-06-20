import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, Check } from "lucide-react"
import { getRoster, addStudent, addCount } from "@/api/omr"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorState } from "@/components/ui/error-state"

// Dedicated "Add students" page (replaces the AddStudent + AddBlankSheets modals
// on the roster page). The individual-add form STAYS on the page and clears after
// each add — rapid sequential entry — with a running list of what was added this
// session. The blank-sheets bulk action is folded in below.
export default function AddStudents() {
  const { id } = useParams()

  const [roster, setRoster] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Individual add
  const [fullName, setFullName] = useState("")
  const [rollNumber, setRollNumber] = useState("")
  const [adding, setAdding] = useState(false)
  const [added, setAdded] = useState([]) // {roll, name} added this session (newest first)

  // Blank sheets
  const [count, setCount] = useState("")
  const [addingBlanks, setAddingBlanks] = useState(false)

  const loadRoster = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setRoster(await getRoster(id))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadRoster()
  }, [loadRoster])

  async function handleAdd(e) {
    e.preventDefault()
    if (!rollNumber.trim()) {
      toast.error("Roll number is required")
      return
    }
    setAdding(true)
    try {
      await addStudent({
        roster: id,
        full_name: fullName.trim(),
        roll_number: rollNumber.trim(),
      })
      setAdded((prev) => [{ roll: rollNumber.trim(), name: fullName.trim() }, ...prev])
      toast.success("Student added")
      setFullName("")
      setRollNumber("")
    } catch (err) {
      const detail =
        err.response?.data?.roll_number?.[0] ||
        err.response?.data?.detail ||
        "Failed to add student"
      toast.error(detail)
    } finally {
      setAdding(false)
    }
  }

  async function handleAddBlanks(e) {
    e.preventDefault()
    const n = parseInt(count, 10)
    if (!n || n < 1) {
      toast.error("Enter a number of sheets")
      return
    }
    setAddingBlanks(true)
    try {
      await addCount(id, n)
      toast.success(`Added ${n} blank sheet${n !== 1 ? "s" : ""}`)
      setCount("")
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add blank sheets")
    } finally {
      setAddingBlanks(false)
    }
  }

  if (loading) {
    return (
      <PageShell>
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </PageShell>
    )
  }

  if (error || !roster) {
    return (
      <PageShell>
        <ErrorState
          title="Couldn't load roster"
          description="Something went wrong while loading this roster."
          onRetry={loadRoster}
        />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <PageHeader
        title="Add students"
        description={roster.name}
        actions={
          <Button variant="outline" asChild className="min-h-[40px]">
            <Link to={`/rosters/${id}`}>
              <ArrowLeft className="size-4" aria-hidden="true" /> Done
            </Link>
          </Button>
        }
      />

      {/* Individual add — form stays put for rapid entry */}
      <section className="space-y-4 rounded-xl border border-border p-4 sm:p-5">
        <div>
          <h2 className="text-sm font-semibold">Add a student</h2>
          <p className="text-sm text-muted-foreground">
            The form stays here after each add, so you can enter several in a row.
          </p>
        </div>
        <form onSubmit={handleAdd} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="student-name">Full name (optional)</Label>
            <Input
              id="student-name"
              placeholder="e.g. Asha Devi"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="roll_number">Roll number</Label>
            <Input
              id="roll_number"
              placeholder="e.g. 101"
              value={rollNumber}
              onChange={(e) => setRollNumber(e.target.value)}
            />
          </div>
          <Button
            type="submit"
            disabled={adding || !rollNumber.trim()}
            className="min-h-[44px] sm:min-h-[40px]"
          >
            {adding ? "Adding…" : "Add student"}
          </Button>
        </form>

        {added.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">
              Added this session ({added.length})
            </p>
            <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
              {added.map((s, i) => (
                <li
                  key={`${s.roll}-${i}`}
                  className="flex items-center gap-2 px-3 py-2 text-sm"
                >
                  <Check
                    className="size-4 shrink-0 text-[var(--color-success)]"
                    aria-hidden="true"
                  />
                  <span className="font-mono text-xs font-medium">{s.roll}</span>
                  <span className="truncate text-muted-foreground">{s.name || "—"}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Blank sheets — numbered students with blank names */}
      <section className="space-y-4 rounded-xl border border-border p-4 sm:p-5">
        <div>
          <h2 className="text-sm font-semibold">Add blank sheets</h2>
          <p className="text-sm text-muted-foreground">
            Creates N numbered students with blank names (roll numbers 1–N).
          </p>
        </div>
        <form onSubmit={handleAddBlanks} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="space-y-1.5 sm:max-w-[200px]">
            <Label htmlFor="sheet-count">Number of sheets</Label>
            <Input
              id="sheet-count"
              type="number"
              min="1"
              max="10"
              placeholder="e.g. 5"
              value={count}
              onChange={(e) => setCount(e.target.value)}
            />
          </div>
          <Button
            type="submit"
            variant="outline"
            disabled={addingBlanks || !count || parseInt(count, 10) < 1}
            className="min-h-[44px] sm:min-h-[40px]"
          >
            {addingBlanks ? "Adding…" : "Add sheets"}
          </Button>
        </form>
      </section>
    </PageShell>
  )
}
