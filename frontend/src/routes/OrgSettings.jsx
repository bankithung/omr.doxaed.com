import { useEffect, useState, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import {
  updateOrg,
  deleteOrg,
  getOrgBranding,
  updateOrgBranding,
} from "@/api/orgs"
import { mediaUrl } from "@/api/omr"
import { useOrg } from "@/org/OrgContext"
import { useAuth } from "@/auth/AuthContext"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

const TYPES = [
  ["personal", "Personal"],
  ["school", "School"],
  ["college", "College"],
  ["university", "University"],
  ["coaching", "Coaching"],
  ["other", "Other"],
]

export default function OrgSettings() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { activeOrg, refreshOrgs, setActiveOrg } = useOrg() ?? {}
  const { user } = useAuth()

  const [name, setName] = useState("")
  const [type, setType] = useState("other")
  const [savingGeneral, setSavingGeneral] = useState(false)

  const [heading, setHeading] = useState("")
  const [logoUrl, setLogoUrl] = useState(null)
  const [logoFile, setLogoFile] = useState(null)
  const [savingBrand, setSavingBrand] = useState(false)
  const logoRef = useRef(null)

  const [deleteOpen, setDeleteOpen] = useState(false)
  const [confirmName, setConfirmName] = useState("")
  const [deleting, setDeleting] = useState(false)

  const isOwner = Boolean(user && activeOrg && user.id === activeOrg.owner)

  useEffect(() => {
    if (activeOrg) {
      setName(activeOrg.name ?? "")
      setType(activeOrg.type ?? "other")
    }
  }, [activeOrg])

  useEffect(() => {
    getOrgBranding(id)
      .then((d) => {
        setHeading(d.default_sheet_heading ?? "")
        setLogoUrl(d.logo ?? null)
      })
      .catch(() => {})
  }, [id])

  async function saveGeneral(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Name is required")
      return
    }
    setSavingGeneral(true)
    try {
      await updateOrg(id, { name: name.trim(), type })
      await refreshOrgs({ force: true })
      toast.success("Organization updated")
    } catch {
      toast.error("Failed to update organization")
    } finally {
      setSavingGeneral(false)
    }
  }

  async function saveBranding(e) {
    e.preventDefault()
    setSavingBrand(true)
    try {
      if (logoFile) {
        const fd = new FormData()
        fd.append("default_sheet_heading", heading)
        fd.append("logo", logoFile)
        await updateOrgBranding(id, fd)
      } else {
        await updateOrgBranding(id, { default_sheet_heading: heading })
      }
      const d = await getOrgBranding(id)
      setLogoUrl(d.logo ?? null)
      setLogoFile(null)
      if (logoRef.current) logoRef.current.value = ""
      toast.success("Branding saved")
    } catch {
      toast.error("Failed to save branding")
    } finally {
      setSavingBrand(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteOrg(id)
      toast.success("Organization deleted")
      setActiveOrg(null)
      await refreshOrgs({ force: true })
      navigate("/organizations")
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to delete organization")
      setDeleting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader title="Organization settings" description={activeOrg?.name} />

      {/* General */}
      <section className="max-w-lg space-y-4 rounded-xl border border-border p-4 sm:p-5">
        <h2 className="text-sm font-semibold">General</h2>
        <form onSubmit={saveGeneral} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="org-name">Name</Label>
            <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="org-type">Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger id="org-type" className="min-h-[40px] w-full">
                <SelectValue placeholder="Select a type…" />
              </SelectTrigger>
              <SelectContent>
                {TYPES.map(([v, l]) => (
                  <SelectItem key={v} value={v}>{l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Changing the type only updates default labels for new groups; existing names are kept.
            </p>
          </div>
          <Button type="submit" disabled={savingGeneral} className="min-h-[40px]">
            {savingGeneral ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </section>

      {/* Branding */}
      <section className="max-w-lg space-y-4 rounded-xl border border-border p-4 sm:p-5">
        <div>
          <h2 className="text-sm font-semibold">Sheet branding</h2>
          <p className="text-sm text-muted-foreground">
            The default heading + logo printed on OMR sheets across this organization.
          </p>
        </div>
        <form onSubmit={saveBranding} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="org-heading">Default sheet heading</Label>
            <Input
              id="org-heading"
              placeholder="e.g. Riverdale High School"
              value={heading}
              onChange={(e) => setHeading(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Logo</Label>
            {logoUrl && !logoFile && (
              <img
                src={mediaUrl(logoUrl)}
                alt="Organization logo"
                className="mb-1 size-12 rounded border border-border bg-surface-2 object-contain"
              />
            )}
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-[40px]"
                onClick={() => logoRef.current?.click()}
              >
                {logoFile ? "Change logo" : logoUrl ? "Replace logo" : "Upload logo"}
              </Button>
              {logoFile && (
                <span className="max-w-[180px] truncate text-sm text-muted-foreground">{logoFile.name}</span>
              )}
            </div>
            <input
              ref={logoRef}
              type="file"
              accept="image/png,image/jpeg"
              className="sr-only"
              aria-label="Upload organization logo"
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null
                if (f && f.size > 2 * 1024 * 1024) {
                  toast.error("Logo must be 2 MB or smaller")
                  e.target.value = ""
                  return
                }
                setLogoFile(f)
              }}
            />
            <p className="text-xs text-muted-foreground">PNG or JPEG, max 2 MB</p>
          </div>
          <Button type="submit" disabled={savingBrand} className="min-h-[40px]">
            {savingBrand ? "Saving…" : "Save branding"}
          </Button>
        </form>
      </section>

      {/* Danger zone — owner only */}
      {isOwner && (
        <section className="max-w-lg space-y-3 rounded-xl border border-destructive/40 p-4 sm:p-5">
          <div>
            <h2 className="text-sm font-semibold text-destructive">Delete organization</h2>
            <p className="text-sm text-muted-foreground">
              Permanently deletes <strong>{activeOrg?.name}</strong> and all its classes, exams, students
              and members. This can't be undone.
            </p>
          </div>
          <Button
            variant="destructive"
            className="min-h-[40px]"
            onClick={() => {
              setConfirmName("")
              setDeleteOpen(true)
            }}
          >
            Delete organization
          </Button>
        </section>
      )}

      <Dialog open={deleteOpen} onOpenChange={(o) => !deleting && setDeleteOpen(o)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete organization</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Type <strong>{activeOrg?.name}</strong> to confirm. This deletes everything in it.
          </p>
          <Input
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
            placeholder={activeOrg?.name}
            aria-label="Confirm organization name"
          />
          <DialogFooter showCloseButton>
            <Button
              variant="destructive"
              disabled={deleting || confirmName !== activeOrg?.name}
              onClick={handleDelete}
            >
              {deleting ? "Deleting…" : "Delete organization"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
