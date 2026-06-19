import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { FileTextIcon } from "lucide-react"
import { listClasses, createClass } from "@/api/assessments"
import { listFolders } from "@/api/folders"
import { useOrg } from "@/org/OrgContext"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { DataTable } from "@/components/ui/DataTable"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"

// Sentinel value for the "No folder" option (radix Select disallows empty-string values).
const NO_FOLDER = "__none__"

const COLUMNS = [
  {
    key: "name",
    header: "Name",
    cell: (cls) => (
      <Link
        to={`/classes/${cls.id}`}
        className="font-medium hover:text-primary hover:underline"
      >
        {cls.name}
      </Link>
    ),
  },
  {
    key: "description",
    header: "Description",
    cell: (cls) =>
      cls.description ? (
        <span className="text-muted-foreground">{cls.description}</span>
      ) : (
        <span className="italic text-muted-foreground">No description</span>
      ),
  },
  {
    key: "actions",
    header: "",
    mobileLabel: "",
    cell: (cls) => (
      <Button asChild variant="outline" size="sm" className="min-h-[40px]">
        <Link to={`/classes/${cls.id}`}>View</Link>
      </Button>
    ),
    className: "w-24 text-right",
  },
]

export default function Classes() {
  const { activeOrg } = useOrg() ?? {}
  // A non-admin org member only sees classes an admin granted them (or ones they
  // created). When they have none, point them at the admin rather than implying
  // the list is simply empty.
  const isOrgMember = Boolean(activeOrg) && activeOrg.role !== "admin"
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [folderId, setFolderId] = useState(NO_FOLDER)
  const [folders, setFolders] = useState([])
  const [submitting, setSubmitting] = useState(false)

  async function fetchClasses() {
    setLoading(true)
    setError(false)
    try {
      const data = await listClasses()
      setClasses(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load classes")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClasses()
    // Folders are optional — silently ignore failures (e.g. solo scope quirks).
    listFolders()
      .then((data) => setFolders(data.results ?? data))
      .catch(() => setFolders([]))
  }, [])

  function openDialog() {
    setName("")
    setDescription("")
    setFolderId(NO_FOLDER)
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
      const payload = { name: name.trim(), description: description.trim() }
      // Folder is optional and additive — only sent when explicitly chosen.
      if (folderId !== NO_FOLDER) payload.folder = Number(folderId)
      await createClass(payload)
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
    <PageShell>
      <PageHeader
        title="Classes"
        description="Manage your class groups"
        actions={<Button onClick={openDialog}>Create class</Button>}
      />

      {!loading && !error && classes.length > 0 && (
        <div className="-mb-4">
          <Badge variant="neutral" className="tabular">
            {classes.length} {classes.length === 1 ? "class" : "classes"}
          </Badge>
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={classes}
        getRowKey={(cls) => cls.id}
        loading={loading}
        error={error}
        onRetry={fetchClasses}
        empty={{
          icon: FileTextIcon,
          title: "No classes yet",
          description: isOrgMember
            ? "Ask an admin to grant you access to a class, or create your own."
            : "Create your first class to get started.",
          action: <Button onClick={openDialog}>Create class</Button>,
        }}
      />

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
            {folders.length > 0 && (
              <div className="space-y-1.5">
                <Label htmlFor="class-folder">Folder (optional)</Label>
                <Select value={folderId} onValueChange={setFolderId}>
                  <SelectTrigger id="class-folder" className="w-full">
                    <SelectValue placeholder="No folder" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NO_FOLDER}>No folder</SelectItem>
                    {folders.map((f) => (
                      <SelectItem key={f.id} value={String(f.id)}>
                        {f.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <DialogFooter showCloseButton>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
