import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { listClasses, createClass } from "@/api/assessments"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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

export default function Classes() {
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function fetchClasses() {
    try {
      const data = await listClasses()
      setClasses(data.results ?? data)
    } catch {
      toast.error("Failed to load classes")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClasses()
  }, [])

  function openDialog() {
    setName("")
    setDescription("")
    setDialogOpen(true)
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Class name is required")
      return
    }
    setSubmitting(true)
    try {
      await createClass({ name: name.trim(), description: description.trim() })
      toast.success("Class created")
      setDialogOpen(false)
      fetchClasses()
    } catch {
      toast.error("Failed to create class")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Classes</h1>
          <p className="text-sm text-muted-foreground">Manage your class groups</p>
        </div>
        <Button onClick={openDialog}>Create class</Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : classes.length === 0 ? (
        <EmptyState
          title="No classes yet"
          description="Create your first class to get started."
          action={<Button onClick={openDialog}>Create class</Button>}
        />
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="w-24 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {classes.map((cls) => (
                <TableRow key={cls.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/classes/${cls.id}`}
                      className="hover:text-primary hover:underline"
                    >
                      {cls.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {cls.description || <span className="italic">No description</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/classes/${cls.id}`}>View</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create class</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="class-name">Name</Label>
              <Input
                id="class-name"
                placeholder="e.g. Class 8A"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="class-desc">Description (optional)</Label>
              <Textarea
                id="class-desc"
                placeholder="Short description of this class"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
            <DialogFooter showCloseButton>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
