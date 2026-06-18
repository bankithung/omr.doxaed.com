import { useEffect, useState, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { useOrg } from "@/org/OrgContext"
import { getMembers, invite, setMemberRole, removeMember, getOrgBranding, updateOrgBranding } from "@/api/orgs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
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
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/list-skeletons"
import { ChevronDownIcon, UserPlusIcon, CreditCardIcon, ClipboardListIcon, UsersIcon } from "lucide-react"

const ROLES = ["admin", "member"]
const ROLE_LABELS = { admin: "Admin", member: "Member" }

// ─── OrgBrandingCard — admin-only section ─────────────────────────────────────

function OrgBrandingCard({ orgId }) {
  const [heading, setHeading] = useState("")
  const [logoFile, setLogoFile] = useState(null)
  const [currentLogoUrl, setCurrentLogoUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const logoInputRef = useRef(null)

  useEffect(() => {
    getOrgBranding(orgId)
      .then((data) => {
        setHeading(data.default_sheet_heading ?? "")
        setCurrentLogoUrl(data.logo ?? null)
      })
      .catch(() => toast.error("Failed to load branding settings"))
      .finally(() => setLoading(false))
  }, [orgId])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    try {
      let data
      if (logoFile) {
        data = new FormData()
        data.append("default_sheet_heading", heading.trim())
        data.append("logo", logoFile)
      } else {
        data = { default_sheet_heading: heading.trim() }
      }
      const result = await updateOrgBranding(orgId, data)
      setCurrentLogoUrl(result.logo ?? null)
      setLogoFile(null)
      if (logoInputRef.current) logoInputRef.current.value = ""
      toast.success("Branding settings saved")
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to save branding"
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl border p-4">
        <p className="text-sm text-muted-foreground">Loading branding settings…</p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSave} className="rounded-xl border p-4 space-y-4">
      <p className="text-sm font-semibold">Organisation branding</p>
      <p className="text-xs text-muted-foreground">
        Applied to all sheets generated under this organisation (unless overridden per test).
      </p>

      <div className="space-y-1.5">
        <Label htmlFor="org-heading">Default sheet heading</Label>
        <Input
          id="org-heading"
          placeholder="e.g. Springfield School District"
          value={heading}
          onChange={(e) => setHeading(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label>Organisation logo</Label>
        {currentLogoUrl && (
          <div className="rounded-lg border p-2 inline-block">
            <img
              src={currentLogoUrl}
              alt="Current organisation logo"
              className="h-12 w-auto object-contain"
            />
          </div>
        )}
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-[40px]"
            onClick={() => logoInputRef.current?.click()}
          >
            {logoFile ? "Change logo" : currentLogoUrl ? "Replace logo" : "Upload logo"}
          </Button>
          {logoFile && (
            <span className="text-sm text-muted-foreground truncate max-w-[180px]">
              {logoFile.name}
            </span>
          )}
          {logoFile && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setLogoFile(null)
                if (logoInputRef.current) logoInputRef.current.value = ""
              }}
            >
              Remove
            </Button>
          )}
        </div>
        {/* Hidden native file input — custom trigger button above */}
        <input
          ref={logoInputRef}
          type="file"
          accept="image/png,image/jpeg"
          className="sr-only"
          onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
          aria-label="Upload organisation logo"
        />
        <p className="text-xs text-muted-foreground">PNG or JPEG, max 2 MB</p>
      </div>

      <Button type="submit" size="sm" disabled={saving} className="min-h-[40px]">
        {saving ? "Saving…" : "Save branding"}
      </Button>
    </form>
  )
}

export default function OrgMembers() {
  const { id: orgId } = useParams()
  const { orgs } = useOrg()
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Invite dialog
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("member")
  const [inviting, setInviting] = useState(false)

  // Remove confirm dialog
  const [removeTarget, setRemoveTarget] = useState(null) // member object
  const [removing, setRemoving] = useState(false)

  const org = orgs.find((o) => String(o.id) === String(orgId))
  const isAdmin = org?.role === "admin"

  async function fetchMembers() {
    setLoading(true)
    setError(false)
    try {
      const data = await getMembers(orgId)
      setMembers(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load members")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMembers()
  }, [orgId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleInvite(e) {
    e.preventDefault()
    if (!inviteEmail.trim()) {
      toast.error("Email is required")
      return
    }
    setInviting(true)
    try {
      await invite(orgId, inviteEmail.trim(), inviteRole)
      toast.success(`Invitation sent to ${inviteEmail.trim()}`)
      setInviteOpen(false)
      setInviteEmail("")
      setInviteRole("member")
      fetchMembers()
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.email?.[0] ||
        "Failed to send invitation"
      toast.error(msg)
    } finally {
      setInviting(false)
    }
  }

  async function handleRoleChange(member, newRole) {
    try {
      await setMemberRole(orgId, member.user_id ?? member.id, newRole)
      toast.success(`${member.email} is now ${ROLE_LABELS[newRole]}`)
      fetchMembers()
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        (err?.response?.status === 400 ? "Cannot demote the last admin" : null) ||
        "Failed to change role"
      toast.error(msg)
    }
  }

  async function handleRemove() {
    if (!removeTarget) return
    setRemoving(true)
    try {
      await removeMember(orgId, removeTarget.user_id ?? removeTarget.id)
      toast.success(`${removeTarget.email} removed`)
      setRemoveTarget(null)
      fetchMembers()
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        (err?.response?.status === 400 ? "Cannot remove the last admin" : null) ||
        (err?.response?.status === 403 ? "Not authorized to remove this member" : null) ||
        "Failed to remove member"
      toast.error(msg)
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{org?.name ?? "Organization"} — Members</h1>
          <p className="text-sm text-muted-foreground">
            {members.length} member{members.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to={`/organizations/${orgId}/billing`}>
              <CreditCardIcon className="mr-1.5" />
              Billing
            </Link>
          </Button>
          {isAdmin && (
            <Button variant="outline" asChild>
              <Link to={`/organizations/${orgId}/audit`}>
                <ClipboardListIcon className="mr-1.5" />
                Audit log
              </Link>
            </Button>
          )}
          {isAdmin && (
            <Button
              onClick={() => {
                setInviteEmail("")
                setInviteRole("member")
                setInviteOpen(true)
              }}
            >
              <UserPlusIcon className="mr-1.5" />
              Invite member
            </Button>
          )}
        </div>
      </div>

      {loading ? (
        <TableSkeleton rows={5} />
      ) : error ? (
        <ErrorState
          title="Couldn't load members"
          description="Something went wrong while loading this organization's members."
          onRetry={fetchMembers}
        />
      ) : members.length === 0 ? (
        <EmptyState
          icon={UsersIcon}
          title="No members yet"
          description="Invite people to join this organization."
          action={
            isAdmin ? (
              <Button onClick={() => setInviteOpen(true)}>Invite member</Button>
            ) : null
          }
        />
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                {isAdmin && <TableHead className="w-24 text-right">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((m) => (
                <TableRow key={m.user_id ?? m.id ?? m.email}>
                  <TableCell className="font-medium">{m.email}</TableCell>
                  <TableCell>
                    {isAdmin ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" size="sm">
                            {ROLE_LABELS[m.role] ?? m.role}
                            <ChevronDownIcon className="ml-1" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start">
                          {ROLES.map((r) => (
                            <DropdownMenuItem
                              key={r}
                              disabled={r === m.role}
                              onSelect={() => handleRoleChange(m, r)}
                            >
                              {ROLE_LABELS[r]}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        {ROLE_LABELS[m.role] ?? m.role}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground capitalize">
                    {m.status ?? "active"}
                  </TableCell>
                  {isAdmin && (
                    <TableCell className="text-right">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setRemoveTarget(m)}
                      >
                        Remove
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Branding settings — admin only (Phase 3c) */}
      {isAdmin && (
        <div className="mt-8">
          <OrgBrandingCard orgId={orgId} />
        </div>
      )}

      {/* Invite dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite member</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleInvite} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="invite-email">Email address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="colleague@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <div className="flex gap-2">
                {ROLES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setInviteRole(r)}
                    className={[
                      "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                      inviteRole === r
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-background text-foreground hover:bg-muted",
                    ].join(" ")}
                  >
                    {ROLE_LABELS[r]}
                  </button>
                ))}
              </div>
            </div>
            <DialogFooter showCloseButton>
              <Button type="submit" disabled={inviting}>
                {inviting ? "Sending…" : "Send invitation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Remove confirm dialog */}
      <Dialog open={!!removeTarget} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove member</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Remove <strong>{removeTarget?.email}</strong> from this organization? This cannot be
            undone.
          </p>
          <DialogFooter showCloseButton>
            <Button variant="destructive" onClick={handleRemove} disabled={removing}>
              {removing ? "Removing…" : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
