import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { EmptyState } from "@/components/ui/empty-state"

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
        <Button variant="outline" size="sm">
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
            <Label htmlFor="roll-number">Roll number</Label>
            <Input
              id="roll-number"
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
        <Button variant="outline" size="sm">
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

export default function RosterDetail() {
  const { id } = useParams()
  const [roster, setRoster] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [rosterData, studentsData] = await Promise.all([
        getRoster(id),
        listStudents(id),
      ])
      setRoster(rosterData)
      setStudents(studentsData.results ?? studentsData)
    } catch {
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
      <div className="mx-auto max-w-4xl px-4 py-8">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Breadcrumb */}
      <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/rosters" className="hover:text-foreground hover:underline">
          Rosters
        </Link>
        <span>/</span>
        <span>{roster?.name ?? "Roster"}</span>
      </div>

      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">{roster?.name ?? "Roster"}</h1>
          <p className="text-sm text-muted-foreground">
            {students.length} student{students.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <AddStudentDialog rosterId={Number(id)} onAdded={fetchData} />
          <AddBlankSheetsDialog rosterId={Number(id)} onAdded={fetchData} />
        </div>
      </div>

      {/* Students table */}
      {students.length === 0 ? (
        <EmptyState
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
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Roll #</TableHead>
                <TableHead>Full name</TableHead>
                <TableHead>Ref</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {students.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-mono font-medium">{s.roll_number}</TableCell>
                  <TableCell>
                    {s.full_name ? (
                      s.full_name
                    ) : (
                      <span className="italic text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {s.external_ref || <span className="italic">—</span>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
