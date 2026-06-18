import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { toast } from "sonner"
import { FolderIcon, Share2Icon, Trash2Icon } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import {
  getFolder,
  deleteFolder,
  listShares,
  createShare,
  deleteShare,
} from "@/api/folders"
import { listClasses, createClass } from "@/api/assessments"
import { getMembers } from "@/api/orgs"
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
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { DataList } from "@/components/ui/data-list"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"

// ─── PermissionSegment — custom VIEW/EDIT segmented control (NO native select) ──

function PermissionSegment({ value, onChange, disabled }) {
  const OPTIONS = [
    { value: "view", label: "View" },
    { value: "edit", label: "Edit" },
  ]
  return (
    <div className="flex rounded-lg border border-border overflow-hidden">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          disabled={disabled}
          onClick={() => onChange(opt.value)}
          aria-pressed={value === opt.value}
          className={[
            "px-3 py-1.5 text-xs font-medium transition-colors min-h-[40px] min-w-[56px]",
            value === opt.value
              ? "bg-primary text-primary-foreground"
              : "bg-background text-foreground hover:bg-muted",
            "border-r last:border-r-0 border-border disabled:opacity-50 disabled:cursor-not-allowed",
          ].join(" ")}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

// ─── ShareRow — one member (or the org-wide row) ────────────────────────────────
//
// Reflects an existing share when present; lets the owner pick VIEW/EDIT and
// toggle Add/Remove. All mutations route through the parent's handlers so the
// share list stays the single source of truth.

function ShareRow({ label, sublabel, share, busy, onAdd, onRemove, onChangePermission }) {
  const shared = Boolean(share)
  const [pendingPerm, setPendingPerm] = useState("view")
  const permission = shared ? share.permission : pendingPerm

  function handlePermissionChange(next) {
    if (shared) {
      onChangePermission(share, next)
    } else {
      setPendingPerm(next)
    }
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{label}</p>
        {sublabel && <p className="truncate text-xs text-muted-foreground">{sublabel}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <PermissionSegment value={permission} onChange={handlePermissionChange} disabled={busy} />
        {shared ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-[40px]"
            disabled={busy}
            onClick={() => onRemove(share)}
          >
            Remove
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            className="min-h-[40px]"
            disabled={busy}
            onClick={() => onAdd(pendingPerm)}
          >
            Add
          </Button>
        )}
      </div>
    </div>
  )
}

// ─── ShareDialog ────────────────────────────────────────────────────────────────

function ShareDialog({ folder, open, onOpenChange }) {
  const { user } = useAuth()
  const { activeOrg } = useOrg()
  const [members, setMembers] = useState([])
  const [shares, setShares] = useState([])
  const [loading, setLoading] = useState(true)
  const [busyKey, setBusyKey] = useState(null) // which row is mid-flight

  const loadShares = useCallback(async () => {
    try {
      const data = await listShares(folder.id)
      setShares(data.results ?? data)
    } catch {
      toast.error("Failed to load existing shares")
    }
  }, [folder.id])

  useEffect(() => {
    if (!open) return
    setLoading(true)
    const memberReq = activeOrg
      ? getMembers(activeOrg.id).then((d) => d.results ?? d).catch(() => [])
      : Promise.resolve([])
    Promise.all([memberReq, loadShares()])
      .then(([m]) => setMembers(m))
      .finally(() => setLoading(false))
  }, [open, activeOrg, loadShares])

  // Index member shares by user id for quick lookup.
  const memberShareByUser = {}
  let orgShare = null
  for (const s of shares) {
    if (s.share_scope === "org") orgShare = s
    else if (s.shared_with != null) memberShareByUser[String(s.shared_with)] = s
  }

  // Exclude yourself from the member list.
  const shareableMembers = members.filter(
    (m) => String(m.user_id ?? m.id) !== String(user?.id),
  )

  async function addMemberShare(member, permission) {
    setBusyKey(`m${member.user_id ?? member.id}`)
    try {
      await createShare(folder.id, {
        shared_with: member.user_id ?? member.id,
        share_scope: "member",
        permission,
      })
      toast.success(`Shared with ${member.email}`)
      await loadShares()
    } catch (err) {
      toast.error(shareErrorMessage(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function addOrgShare(permission) {
    setBusyKey("org")
    try {
      await createShare(folder.id, { share_scope: "org", permission })
      toast.success("Shared with everyone in the organisation")
      await loadShares()
    } catch (err) {
      toast.error(shareErrorMessage(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function removeShare(share, key) {
    setBusyKey(key)
    try {
      await deleteShare(folder.id, share.id)
      toast.success("Share removed")
      await loadShares()
    } catch (err) {
      toast.error(shareErrorMessage(err))
    } finally {
      setBusyKey(null)
    }
  }

  // Changing permission = remove + recreate (no PATCH endpoint for shares).
  async function changeMemberPermission(member, share, permission) {
    setBusyKey(`m${member.user_id ?? member.id}`)
    try {
      await deleteShare(folder.id, share.id)
      await createShare(folder.id, {
        shared_with: member.user_id ?? member.id,
        share_scope: "member",
        permission,
      })
      await loadShares()
    } catch (err) {
      toast.error(shareErrorMessage(err))
    } finally {
      setBusyKey(null)
    }
  }

  async function changeOrgPermission(share, permission) {
    setBusyKey("org")
    try {
      await deleteShare(folder.id, share.id)
      await createShare(folder.id, { share_scope: "org", permission })
      await loadShares()
    } catch (err) {
      toast.error(shareErrorMessage(err))
    } finally {
      setBusyKey(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share “{folder.name}”</DialogTitle>
        </DialogHeader>

        {!activeOrg ? (
          <p className="text-sm text-muted-foreground">
            Folder sharing is only available inside an organisation. Switch to an
            organisation workspace to share this folder.
          </p>
        ) : loading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Org-wide share */}
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Everyone
              </p>
              <ShareRow
                label="Everyone in the organisation"
                sublabel={activeOrg.name}
                share={orgShare}
                busy={busyKey === "org"}
                onAdd={addOrgShare}
                onRemove={(s) => removeShare(s, "org")}
                onChangePermission={(s, perm) => changeOrgPermission(s, perm)}
              />
            </div>

            {/* Member shares */}
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Members
              </p>
              {shareableMembers.length === 0 ? (
                <p className="rounded-lg border border-dashed border-border px-3 py-4 text-center text-sm text-muted-foreground">
                  No other members in this organisation yet. Invite colleagues to
                  share folders with them.
                </p>
              ) : (
                <div className="flex max-h-64 flex-col gap-2 overflow-y-auto">
                  {shareableMembers.map((m) => {
                    const uid = m.user_id ?? m.id
                    const share = memberShareByUser[String(uid)]
                    return (
                      <ShareRow
                        key={uid}
                        label={m.email}
                        sublabel={null}
                        share={share}
                        busy={busyKey === `m${uid}`}
                        onAdd={(perm) => addMemberShare(m, perm)}
                        onRemove={(s) => removeShare(s, `m${uid}`)}
                        onChangePermission={(s, perm) => changeMemberPermission(m, s, perm)}
                      />
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        <DialogFooter showCloseButton />
      </DialogContent>
    </Dialog>
  )
}

// Surface backend share errors inline via toast (never alert). Cross-org grantee
// and other validation come back as 400 with a field/detail message.
function shareErrorMessage(err) {
  const data = err?.response?.data
  return (
    data?.shared_with ||
    data?.detail ||
    data?.folder ||
    data?.share_scope ||
    "Failed to update sharing"
  )
}

// ─── Class columns inside the folder ────────────────────────────────────────────

const CLASS_COLUMNS = [
  {
    key: "name",
    header: "Class",
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

// ─── FolderDetail ────────────────────────────────────────────────────────────────

export default function FolderDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [folder, setFolder] = useState(null)
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const [shareOpen, setShareOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Create-class-here dialog
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [creating, setCreating] = useState(false)

  const canEdit = folder?.permission === "edit"

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [f, clsData] = await Promise.all([
        getFolder(id),
        listClasses({ folder: id }),
      ])
      setFolder(f)
      setClasses(clsData.results ?? clsData)
    } catch {
      setError(true)
      toast.error("Failed to load folder")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteFolder(id)
      toast.success("Folder deleted")
      navigate("/folders")
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        (err?.response?.status === 403
          ? "You have view-only access to this folder."
          : null) ||
        "Failed to delete folder"
      toast.error(msg)
      setDeleting(false)
      setDeleteOpen(false)
    }
  }

  async function handleCreateClass(e) {
    e.preventDefault()
    if (!newName.trim()) {
      toast.error("Class name is required")
      return
    }
    setCreating(true)
    try {
      await createClass({ name: newName.trim(), folder: Number(id) })
      toast.success("Class created in this folder")
      setCreateOpen(false)
      setNewName("")
      fetchData()
    } catch (err) {
      const msg =
        err?.response?.data?.name?.[0] ||
        err?.response?.data?.folder?.[0] ||
        err?.response?.data?.detail ||
        "Failed to create class"
      toast.error(msg)
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 space-y-4">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-64" />
        <div className="space-y-3 pt-4">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <ErrorState
          title="Couldn't load this folder"
          description="Something went wrong while loading the folder. Check your connection and try again."
          onRetry={fetchData}
        />
      </div>
    )
  }

  if (!folder) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <EmptyState
          icon={FolderIcon}
          title="Folder not found"
          description="This folder may have been deleted or you no longer have access."
          action={
            <Button asChild>
              <Link to="/folders">Back to folders</Link>
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Breadcrumb */}
      <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/folders" className="hover:text-foreground hover:underline">
          Folders
        </Link>
        <span>/</span>
        <span className="truncate">{folder.name}</span>
      </div>

      <PageHeader
        className="mb-6"
        title={
          <span className="flex items-center gap-2">
            <FolderIcon className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
            {folder.name}
          </span>
        }
        description={
          folder.share_count > 0
            ? `Shared with ${folder.share_count} ${folder.share_count === 1 ? "recipient" : "recipients"}`
            : "Private folder"
        }
        actions={
          canEdit ? (
            <>
              <Button variant="outline" onClick={() => setShareOpen(true)}>
                <Share2Icon className="mr-1.5 size-4" aria-hidden="true" />
                Share
              </Button>
              <Button
                variant="outline"
                size="icon"
                aria-label="Delete folder"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2Icon className="size-4" aria-hidden="true" />
              </Button>
            </>
          ) : null
        }
      />

      {/* Classes in this folder */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-muted-foreground">Classes in this folder</h2>
        {canEdit && (
          <Button
            size="sm"
            variant="outline"
            className="min-h-[40px]"
            onClick={() => {
              setNewName("")
              setCreateOpen(true)
            }}
          >
            Create class here
          </Button>
        )}
      </div>

      {classes.length === 0 ? (
        <EmptyState
          title="No classes in this folder"
          description={
            canEdit
              ? "Create a class here, or move an existing class into this folder from its edit screen."
              : "This folder has no classes yet."
          }
          action={
            canEdit ? (
              <Button onClick={() => { setNewName(""); setCreateOpen(true) }}>
                Create class here
              </Button>
            ) : null
          }
        />
      ) : (
        <DataList
          columns={CLASS_COLUMNS}
          rows={classes}
          getRowKey={(cls) => cls.id}
        />
      )}

      {/* Share dialog */}
      <ShareDialog
        folder={folder}
        open={shareOpen}
        onOpenChange={setShareOpen}
      />

      {/* Create-class-here dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create class in “{folder.name}”</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateClass} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="folder-class-name">Name</Label>
              <Input
                id="folder-class-name"
                placeholder="e.g. Class 8A"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                autoFocus
              />
            </div>
            <DialogFooter showCloseButton>
              <Button type="submit" disabled={creating}>
                {creating ? "Creating…" : "Create class"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirm dialog (custom — never window.confirm) */}
      <Dialog open={deleteOpen} onOpenChange={(o) => !deleting && setDeleteOpen(o)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete folder</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Delete <strong>{folder.name}</strong>? Classes inside it are not deleted —
            they’ll just no longer belong to a folder. This cannot be undone.
          </p>
          <DialogFooter showCloseButton>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Deleting…" : "Delete folder"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
