import { useEffect, useState, useCallback } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { UsersIcon } from "lucide-react"
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
import { DataTable } from "@/components/ui/DataTable"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"

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
      <span className="text-muted-foreground tabular">
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
  const [error, setError] = useState(false)

  const fetchRosters = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await listRosters()
      setRosters(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load rosters")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRosters()
  }, [fetchRosters])

  return (
    <PageShell>
      <PageHeader
        title="Rosters"
        description="Manage student rosters for OMR sheet generation."
        actions={<CreateRosterDialog onCreated={fetchRosters} />}
      />

      {!loading && !error && rosters.length > 0 && (
        <div className="-mb-4">
          <Badge variant="neutral" className="tabular">
            {rosters.length} {rosters.length === 1 ? "roster" : "rosters"}
          </Badge>
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={rosters}
        getRowKey={(r) => r.id}
        loading={loading}
        error={error}
        onRetry={fetchRosters}
        empty={{
          icon: UsersIcon,
          title: "No rosters yet",
          description: "Create a roster to manage students and generate OMR sheets.",
          action: <CreateRosterDialog onCreated={fetchRosters} />,
        }}
      />
    </PageShell>
  )
}
