import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useOrg } from "@/org/OrgContext"
import {
  getMembers,
  invite,
  setMemberRole,
  removeMember,
} from "@/api/orgs"
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
import { DataTable } from "@/components/ui/DataTable"
import { Badge } from "@/components/ui/badge"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { ChevronDownIcon, UserPlusIcon } from "lucide-react"

const ROLES = ["admin", "member"]
const ROLE_LABELS = { admin: "Admin", member: "Member" }

export default function OrgMembers() {
  const { activeOrg } = useOrg()
  const orgId = activeOrg?.id
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

  const org = activeOrg
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
        (err?.response?.status === 403
          ? "Not authorized to remove this member"
          : null) ||
        "Failed to remove member"
      toast.error(msg)
    } finally {
      setRemoving(false)
    }
  }

  // Columns are derived per-render so they capture isAdmin + handlers.
  const columns = [
    {
      key: "email",
      header: "Email",
      cell: (m) => <span className="font-medium">{m.email}</span>,
    },
    {
      key: "role",
      header: "Role",
      cell: (m) =>
        isAdmin ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="min-h-[40px]">
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
          <Badge variant={m.role === "admin" ? "info" : "neutral"}>
            {ROLE_LABELS[m.role] ?? m.role}
          </Badge>
        ),
    },
    {
      key: "status",
      header: "Status",
      cell: (m) => (
        <span className="text-sm capitalize text-muted-foreground">
          {m.status ?? "active"}
        </span>
      ),
    },
    ...(isAdmin
      ? [
          {
            key: "actions",
            header: "",
            mobileLabel: "",
            cell: (m) => (
              <Button
                variant="destructive"
                size="sm"
                className="min-h-[40px]"
                onClick={() => setRemoveTarget(m)}
              >
                Remove
              </Button>
            ),
            className: "w-24 text-right",
          },
        ]
      : []),
  ]

  return (
    <PageShell>
      <PageHeader
        title="Members"
        description={`${org?.name ?? "Organization"} · ${members.length} member${
          members.length !== 1 ? "s" : ""
        }`}
        actions={
          isAdmin ? (
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
          ) : null
        }
      />

      <DataTable
        columns={columns}
        rows={members}
        getRowKey={(m) => m.user_id ?? m.id ?? m.email}
        loading={loading}
        error={error}
        onRetry={fetchMembers}
        empty={{
          icon: UserPlusIcon,
          title: "No members yet",
          description: "Invite people to join this organization.",
          action: isAdmin ? (
            <Button onClick={() => setInviteOpen(true)}>Invite member</Button>
          ) : null,
        }}
      />

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
                      "min-h-[40px] rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
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
      <Dialog
        open={!!removeTarget}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove member</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Remove <strong>{removeTarget?.email}</strong> from this organization?
            This cannot be undone.
          </p>
          <DialogFooter showCloseButton>
            <Button
              variant="destructive"
              className="bg-destructive text-primary-foreground hover:bg-destructive/90"
              onClick={handleRemove}
              disabled={removing}
            >
              {removing ? "Removing…" : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
