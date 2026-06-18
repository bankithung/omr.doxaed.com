import { useEffect, useState, useCallback } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { listRosters, createRoster } from "@/api/omr"
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
import { DataList } from "@/components/ui/data-list"
import { PageHeader } from "@/components/ui/page-header"

function CreateRosterDialog({ onCreated }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    try {
      await createRoster({ name: name.trim() })
      toast.success("Roster created")
      setName("")
      setOpen(false)
      onCreated()
    } catch {
      toast.error("Failed to create roster")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create roster</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create roster</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="roster-name">Name</Label>
            <Input
              id="roster-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Class 10A"
              required
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={loading || !name.trim()}>
              {loading ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

const COLUMNS = [
  {
    key: "name",
    header: "Name",
    cell: (roster) => (
      <Link
        to={`/rosters/${roster.id}`}
        className="font-medium hover:text-primary hover:underline"
      >
        {roster.name}
      </Link>
    ),
  },
  {
    key: "students",
    header: "Students",
    cell: (roster) => (
      <span className="text-muted-foreground">
        {roster.student_count ?? roster.students_count ?? "—"}
      </span>
    ),
  },
  {
    key: "actions",
    header: "",
    mobileLabel: "",
    cell: (roster) => (
      <Button variant="outline" size="sm" asChild className="min-h-[40px]">
        <Link to={`/rosters/${roster.id}`}>View</Link>
      </Button>
    ),
    className: "w-28 text-right",
  },
]

export default function Rosters() {
  const [rosters, setRosters] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchRosters = useCallback(async () => {
    try {
      const data = await listRosters()
      setRosters(data.results ?? data)
    } catch {
      toast.error("Failed to load rosters")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRosters()
  }, [fetchRosters])

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <PageHeader
        className="mb-6"
        title="Rosters"
        description="Manage student rosters for OMR sheet generation."
        actions={<CreateRosterDialog onCreated={fetchRosters} />}
      />

      {rosters.length === 0 ? (
        <EmptyState
          title="No rosters yet"
          description="Create a roster to manage students and generate OMR sheets."
          action={<CreateRosterDialog onCreated={fetchRosters} />}
        />
      ) : (
        <DataList
          columns={COLUMNS}
          rows={rosters}
          getRowKey={(r) => r.id}
        />
      )}
    </div>
  )
}
