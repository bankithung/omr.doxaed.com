import { useEffect, useState, useCallback } from "react"
import { toast } from "sonner"
import { useOrg } from "@/org/OrgContext"
import {
  getMembers,
  invite,
  setMemberRole,
  removeMember,
  listRoles,
  listRoleBindings,
  createRoleBinding,
  deleteRoleBinding,
} from "@/api/orgs"
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

// Roles whose holders are org admins (keeps the membership admin/member gate in sync).
const ADMIN_ROLE_NAMES = ["Owner", "Admin"]

export default function OrgMembers() {
  const { activeOrg } = useOrg()
  const orgId = activeOrg?.id
  const [members, setMembers] = useState([])
  const [roles, setRoles] = useState([])
  const [bindings, setBindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Invite dialog
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRoleId, setInviteRoleId] = useState("")
  const [inviting, setInviting] = useState(false)

  // Remove confirm dialog
  const [removeTarget, setRemoveTarget] = useState(null) // member object
  const [removing, setRemoving] = useState(false)

  const org = activeOrg
  const isAdmin = org?.role === "admin"

  // Roles assignable on invite / change — exclude Owner (there's exactly one).
  const assignableRoles = roles.filter((r) => r.name !== "Owner")
  const defaultRoleId = String(
    assignableRoles.find((r) => r.name === "Teacher")?.id ?? assignableRoles[0]?.id ?? "",
  )

  const fetchAll = useCallback(async () => {
    if (!orgId) return
    setLoading(true)
    setError(false)
    try {
      const [m, r, b] = await Promise.all([getMembers(orgId), listRoles(), listRoleBindings()])
      setMembers(m.results ?? m)
      setRoles(r.results ?? r)
      setBindings(b.results ?? b)
    } catch {
      setError(true)
      toast.error("Failed to load members")
    } finally {
      setLoading(false)
    }
  }, [orgId])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // The member's org-wide role = their binding with no scope; else fall back to
  // the coarse membership role for legacy members without a binding.
  function orgWideRoleName(m) {
    const userId = m.user_id ?? m.id
    const b = bindings.find((bb) => String(bb.user) === String(userId) && !bb.scope_group)
    if (b) return b.role_name
    return m.role === "admin" ? "Admin" : "Member"
  }

  async function handleInvite(e) {
    e.preventDefault()
    if (!inviteEmail.trim()) {
      toast.error("Email is required")
      return
    }
    const roleId = inviteRoleId || defaultRoleId
    if (!roleId) {
      toast.error("Pick a role")
      return
    }
    setInviting(true)
    try {
      await invite(orgId, inviteEmail.trim(), roleId)
      toast.success(`Invitation sent to ${inviteEmail.trim()}`)
      setInviteOpen(false)
      setInviteEmail("")
      setInviteRoleId("")
      fetchAll()
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          err?.response?.data?.email?.[0] ||
          "Failed to send invitation",
      )
    } finally {
      setInviting(false)
    }
  }

  async function handleRoleChange(member, newRoleId) {
    const userId = member.user_id ?? member.id
    const role = roles.find((r) => String(r.id) === String(newRoleId))
    const membershipRole = ADMIN_ROLE_NAMES.includes(role?.name) ? "admin" : "member"
    try {
      // Sync the coarse role first — this enforces last-admin protection.
      await setMemberRole(orgId, userId, membershipRole)
      // Replace the member's org-wide binding with the new role.
      const existing = bindings.filter(
        (b) => String(b.user) === String(userId) && !b.scope_group,
      )
      for (const b of existing) await deleteRoleBinding(b.id)
      await createRoleBinding({ user: userId, role: newRoleId, scope_group: null })
      toast.success(`${member.email} is now ${role?.name}`)
      fetchAll()
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          (err?.response?.status === 400 ? "Cannot demote the last admin" : "Failed to change role"),
      )
    }
  }

  async function handleRemove() {
    if (!removeTarget) return
    setRemoving(true)
    try {
      await removeMember(orgId, removeTarget.user_id ?? removeTarget.id)
      toast.success(`${removeTarget.email} removed`)
      setRemoveTarget(null)
      fetchAll()
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
          (err?.response?.status === 400 ? "Cannot remove the last admin" : null) ||
          (err?.response?.status === 403 ? "Not authorized to remove this member" : null) ||
          "Failed to remove member",
      )
    } finally {
      setRemoving(false)
    }
  }

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
                {orgWideRoleName(m)}
                <ChevronDownIcon className="ml-1" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {roles.map((r) => (
                <DropdownMenuItem
                  key={r.id}
                  disabled={r.name === orgWideRoleName(m)}
                  onSelect={() => handleRoleChange(m, r.id)}
                >
                  {r.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Badge variant="info">{orgWideRoleName(m)}</Badge>
        ),
    },
    {
      key: "status",
      header: "Status",
      cell: (m) => (
        <span className="text-sm capitalize text-muted-foreground">{m.status ?? "active"}</span>
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
                setInviteRoleId(defaultRoleId)
                setInviteOpen(true)
              }}
            >
              <UserPlusIcon className="mr-1.5" />
              Invite member
            </Button>
          ) : null
        }
      />

      <p className="text-sm text-muted-foreground">
        Each member holds an organization role. Scope someone to specific classes in{" "}
        <strong>Roles &amp; permissions → Member roles</strong>.
      </p>

      <DataTable
        columns={columns}
        rows={members}
        getRowKey={(m) => m.user_id ?? m.id ?? m.email}
        loading={loading}
        error={error}
        onRetry={fetchAll}
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
              <Label htmlFor="invite-role">Role</Label>
              <Select value={inviteRoleId || defaultRoleId} onValueChange={setInviteRoleId}>
                <SelectTrigger id="invite-role" className="min-h-[40px] w-full">
                  <SelectValue placeholder="Select a role…" />
                </SelectTrigger>
                <SelectContent>
                  {assignableRoles.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Sets what they can do org-wide. You can scope them to specific classes later.
              </p>
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
            Remove <strong>{removeTarget?.email}</strong> from this organization? This cannot be undone.
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
