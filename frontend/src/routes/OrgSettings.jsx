import { useEffect, useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
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
import { cn } from "@/lib/utils"

const TYPES = [
  ["personal", "Personal"],
  ["school", "School"],
  ["college", "College"],
  ["university", "University"],
  ["coaching", "Coaching"],
  ["other", "Other"],
]

// A Supabase-style settings row: title + description on the left, a card with the
// fields (and an optional footer action bar) on the right.
function SettingsSection({ title, description, children, footer, danger = false }) {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-3 lg:gap-8">
      <div>
        <h2 className={cn("text-sm font-semibold", danger && "text-destructive")}>{title}</h2>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="lg:col-span-2">
        <div
          className={cn(
            "overflow-hidden rounded-xl border bg-surface-1",
            danger ? "border-destructive/40" : "border-border",
          )}
        >
          <div className="space-y-4 p-4 sm:p-5">{children}</div>
          {footer && (
            <div
              className={cn(
                "flex items-center justify-end border-t px-4 py-3 sm:px-5",
                danger ? "border-destructive/30 bg-destructive/5" : "border-border bg-surface-2/40",
              )}
            >
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function OrgSettings() {
  const navigate = useNavigate()
  const { activeOrg, refreshOrgs, setActiveOrg } = useOrg() ?? {}
  const { user } = useAuth()
  const id = activeOrg?.id

  const [name, setName] = useState("")
  const [slug, setSlug] = useState("")
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
      setSlug(activeOrg.slug ?? "")
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
      const updated = await updateOrg(id, { name: name.trim(), slug: slug.trim(), type })
      await refreshOrgs({ force: true })
      toast.success("Organization updated")
      // The URL carries the slug — follow it if the slug changed.
      if (updated?.slug && updated.slug !== activeOrg?.slug) {
        navigate(`/org/${updated.slug}/settings`, { replace: true })
      }
    } catch (err) {
      toast.error(
        err?.response?.data?.slug?.[0] || err?.response?.data?.detail || "Failed to update organization",
      )
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

      <div className="space-y-8">
        {/* General */}
        <form onSubmit={saveGeneral}>
          <SettingsSection
            title="General"
            description="Your organization's name, URL and type."
            footer={
              <Button type="submit" disabled={savingGeneral} className="min-h-[40px]">
                {savingGeneral ? "Saving…" : "Save changes"}
              </Button>
            }
          >
            <div className="space-y-1.5">
              <Label htmlFor="org-name">Name</Label>
              <Input id="org-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="org-slug">Slug</Label>
              <div className="flex h-10 items-center overflow-hidden rounded-lg border border-input bg-transparent focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/40">
                <span className="select-none border-r border-input px-3 text-sm text-muted-foreground">
                  /org/
                </span>
                <input
                  id="org-slug"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  className="h-full min-w-0 flex-1 bg-transparent px-3 text-sm outline-none"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Used in your organization's URL. Lowercase letters, numbers and hyphens.
              </p>
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
          </SettingsSection>
        </form>

        {/* Sheet branding */}
        <form onSubmit={saveBranding}>
          <SettingsSection
            title="Sheet branding"
            description="The default heading and logo printed on OMR sheets across this organization."
            footer={
              <Button type="submit" disabled={savingBrand} className="min-h-[40px]">
                {savingBrand ? "Saving…" : "Save branding"}
              </Button>
            }
          >
            <div className="space-y-1.5">
              <Label htmlFor="org-heading">Default sheet heading</Label>
              <Input
                id="org-heading"
                placeholder="e.g. Riverdale High School"
                value={heading}
                onChange={(e) => setHeading(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Logo</Label>
              <div className="flex items-center gap-4">
                <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-lg border border-border bg-surface-2">
                  {logoUrl && !logoFile ? (
                    <img src={mediaUrl(logoUrl)} alt="Organization logo" className="size-full object-contain p-1" />
                  ) : (
                    <span className="text-lg font-bold text-muted-foreground">
                      {(activeOrg?.name?.[0] ?? "O").toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="min-w-0 space-y-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="min-h-[40px]"
                    onClick={() => logoRef.current?.click()}
                  >
                    {logoFile ? "Change logo" : logoUrl ? "Replace logo" : "Upload logo"}
                  </Button>
                  <p className="truncate text-xs text-muted-foreground">
                    {logoFile ? logoFile.name : "PNG or JPEG, max 2 MB"}
                  </p>
                </div>
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
            </div>
          </SettingsSection>
        </form>

        {/* Danger zone */}
        {isOwner && (
          <SettingsSection
            title="Danger zone"
            description="Irreversible and destructive actions."
            danger
            footer={
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
            }
          >
            <p className="text-sm text-muted-foreground">
              Permanently deletes <strong className="text-foreground">{activeOrg?.name}</strong> and all its
              classes, exams, students and members. This <strong className="text-foreground">cannot be undone</strong>.
            </p>
          </SettingsSection>
        )}
      </div>

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
