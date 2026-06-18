import { useEffect, useState, useCallback } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { UsersIcon } from "lucide-react"
import { getRoster, listStudents, addStudent, addCount } from "@/api/omr"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/skeletons"
import { Skeleton } from "@/components/ui/skeleton"
import { DataTable } from "@/components/ui/DataTable"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

function AddStudentDialog({ rosterId, onAdded }) {
  const [open, setOpen] = useState(false)
  const [fullName, setFullName] = useState("")
  const [rollNumber, setRollNumber] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!rollNumber.trim()) return
    setLoading(true)
    try {
      await addStudent({
        roster: rosterId,
        full_name: fullName.trim(),
        roll_number: rollNumber.trim(),
      })
      toast.success("Student added")
      setFullName("")
      setRollNumber("")
      setOpen(false)
      onAdded()
    } catch (err) {
      const detail =
        err.response?.data?.roll_number?.[0] ||
        err.response?.data?.detail ||
        "Failed to add student"
      toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="min-h-[40px]">
          Add student
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add student</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="student-name">Full name</Label>
            <Input
              id="student-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Asha Devi"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="roll_number">Roll number</Label>
            <Input
              id="roll_number"
              value={rollNumber}
              onChange={(e) => setRollNumber(e.target.value)}
              placeholder="e.g. 101"
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading || !rollNumber.trim()}>
              {loading ? "Adding…" : "Add student"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function AddBlankSheetsDialog({ rosterId, onAdded }) {
  const [open, setOpen] = useState(false)
  const [count, setCount] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    const n = parseInt(count, 10)
    if (!n || n < 1) return
    setLoading(true)
    try {
      await addCount(rosterId, n)
      toast.success(`Added ${n} blank sheet${n !== 1 ? "s" : ""}`)
      setCount("")
      setOpen(false)
      onAdded()
    } catch (err) {
      const detail = err.response?.data?.detail || "Failed to add blank sheets"
      toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="min-h-[40px]">
          Add blank sheets
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add blank sheets</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Creates N numbered students with blank names (roll numbers 1–N).
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sheet-count">Number of sheets</Label>
            <Input
              id="sheet-count"
              type="number"
              min="1"
              max="10"
              value={count}
              onChange={(e) => setCount(e.target.value)}
              placeholder="e.g. 5"
              required
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button
              type="submit"
              disabled={loading || !count || parseInt(count, 10) < 1}
            >
              {loading ? "Adding…" : "Add sheets"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

const STUDENT_COLUMNS = [
  {
    key: "roll",
    header: "Roll #",
    cell: (s) => (
      <span className="font-mono text-xs font-medium">{s.roll_number}</span>
    ),
  },
  {
    key: "name",
    header: "Full name",
    cell: (s) =>
      s.full_name ? (
        s.full_name
      ) : (
        <span className="italic text-muted-foreground">—</span>
      ),
  },
  {
    key: "ref",
    header: "Ref",
    cell: (s) => (
      <span className="text-muted-foreground">
        {s.external_ref || <span className="italic">—</span>}
      </span>
    ),
  },
]

export default function RosterDetail() {
  const { id } = useParams()
  const [roster, setRoster] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [rosterData, studentsData] = await Promise.all([
        getRoster(id),
        listStudents(id),
      ])
      setRoster(rosterData)
      setStudents(studentsData.results ?? studentsData)
    } catch {
      setError(true)
      toast.error("Failed to load roster data")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <PageShell>
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <TableSkeleton rows={4} />
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Couldn't load roster"
          description="Something went wrong while loading this roster."
          onRetry={fetchData}
        />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <PageHeader
        title={roster?.name ?? "Roster"}
        description={`${students.length} student${students.length !== 1 ? "s" : ""}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <AddStudentDialog rosterId={Number(id)} onAdded={fetchData} />
            <AddBlankSheetsDialog rosterId={Number(id)} onAdded={fetchData} />
          </div>
        }
      />

      {students.length === 0 ? (
        <EmptyState
          icon={UsersIcon}
          title="No students yet"
          description="Add individual students or create numbered blank sheets."
          action={
            <div className="flex gap-2">
              <AddStudentDialog rosterId={Number(id)} onAdded={fetchData} />
              <AddBlankSheetsDialog rosterId={Number(id)} onAdded={fetchData} />
            </div>
          }
        />
      ) : (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground">Students</h2>
          <DataTable
            columns={STUDENT_COLUMNS}
            rows={students}
            getRowKey={(s) => s.id}
          />
        </section>
      )}
    </PageShell>
  )
}
