import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { FolderIcon } from "lucide-react"
import { useOrg } from "@/org/OrgContext"
import { listFolders, createFolder } from "@/api/folders"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { DataTable } from "@/components/ui/DataTable"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"

// ─── Permission badge ─────────────────────────────────────────────────────────
// `permission` is "edit" | "view"; the folder creator gets "edit". We surface a
// clear human label. (Backend does not flag "owner" separately, so creator +
// admins simply read as "Can edit".)

function PermissionBadge({ permission }) {
  if (permission === "edit") {
    return <Badge variant="success">Can edit</Badge>
  }
  return <Badge variant="neutral">View</Badge>
}

// ─── Columns ──────────────────────────────────────────────────────────────────

const COLUMNS = [
  {
    key: "name",
    header: "Name",
    cell: (folder) => (
      <Link
        to={`/folders/${folder.id}`}
        className="flex items-center gap-2 font-medium hover:text-primary hover:underline"
      >
        <FolderIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        {folder.name}
      </Link>
    ),
  },
  {
    key: "share_count",
    header: "Shared with",
    cell: (folder) =>
      folder.share_count > 0 ? (
        <span className="text-muted-foreground">
          {folder.share_count} {folder.share_count === 1 ? "share" : "shares"}
        </span>
      ) : (
        <span className="italic text-muted-foreground">Private</span>
      ),
  },
  {
    key: "permission",
    header: "Access",
    cell: (folder) => <PermissionBadge permission={folder.permission} />,
  },
  {
    key: "actions",
    header: "",
    mobileLabel: "",
    cell: (folder) => (
      <Button asChild variant="outline" size="sm" className="min-h-[40px]">
        <Link to={`/folders/${folder.id}`}>Open</Link>
      </Button>
    ),
    className: "w-24 text-right",
  },
]

// ─── Folders list page ──────────────────────────────────────────────────────────

export default function Folders() {
  const { activeOrg, orgs } = useOrg()
  const [folders, setFolders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [name, setName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  // Admin in the active org → backend returns the whole org folder pool.
  const activeOrgData = activeOrg
    ? orgs.find((o) => String(o.id) === String(activeOrg.id))
    : null
  const isAdmin = activeOrgData?.role === "admin"

  async function fetchFolders() {
    setLoading(true)
    setError(false)
    try {
      const data = await listFolders()
      setFolders(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load folders")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFolders()
  }, [])

  function openDialog() {
    setName("")
    setDialogOpen(true)
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Folder name is required")
      return
    }
    setSubmitting(true)
    try {
      await createFolder({ name: name.trim() })
      toast.success("Folder created")
      setDialogOpen(false)
      fetchFolders()
    } catch (err) {
      const msg =
        err?.response?.data?.name?.[0] ||
        err?.response?.data?.detail ||
        "Failed to create folder"
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader
        title="Folders"
        description="Group your classes and share them with your team."
        actions={<Button onClick={openDialog}>New folder</Button>}
      />

      {!loading && !error && folders.length > 0 && (
        <div className="-mb-4 flex flex-wrap items-center gap-2">
          <Badge variant="neutral" className="tabular">
            {folders.length} {folders.length === 1 ? "folder" : "folders"}
          </Badge>
          {isAdmin && (
            <Badge variant="info">Admin: showing all organisation folders</Badge>
          )}
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={folders}
        getRowKey={(folder) => folder.id}
        loading={loading}
        error={error}
        onRetry={fetchFolders}
        empty={{
          icon: FolderIcon,
          title: "No folders yet",
          description:
            "Create a folder to organise your classes — and share whole folders with colleagues.",
          action: <Button onClick={openDialog}>New folder</Button>,
        }}
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New folder</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="folder-name">Name</Label>
              <Input
                id="folder-name"
                placeholder="e.g. Term 1 — Grade 8"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
            <DialogFooter showCloseButton>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating…" : "Create folder"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
