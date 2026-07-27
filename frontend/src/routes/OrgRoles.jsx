import { useEffect, useState, useCallback } from "react"
import { useOrg } from "@/org/OrgContext"
import { toast } from "sonner"
import { X as XIcon, Plus, Check, ShieldCheck } from "lucide-react"
import {
  getMembers,
  listRoles,
  createRole,
  updateRole,
  deleteRole,
  listRoleBindings,
  createRoleBinding,
  deleteRoleBinding,
  getPermissionCatalog,
} from "@/api/orgs"
import { listClasses } from "@/api/assessments"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
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
import { useSubNav } from "@/components/shell/sub-nav-context"

const ROLES_SECTIONS = [
  { key: "roles", label: "Roles" },
  { key: "members", label: "Member roles" },
]
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const ORG_WIDE = "__org__"

// Role create/edit dialog with the grouped permission matrix.
function RoleDialog({ role, catalog, onClose, onSaved }) {
  const editing = !!role
  const [name, setName] = useState(role?.name ?? "")
  const [perms, setPerms] = useState(() => new Set(role?.permissions ?? []))
  const [saving, setSaving] = useState(false)

  const groups = {}
  for (const item of catalog) (groups[item.group] ??= []).push(item)

  function toggle(code) {
    setPerms((p) => {
      const n = new Set(p)
      if (n.has(code)) n.delete(code)
      else n.add(code)
      return n
    })
  }

  async function save() {
    if (!name.trim()) {
      toast.error("Role name is required")
      return
    }
    setSaving(true)
    try {
      const body = { name: name.trim(), permissions: [...perms] }
      if (editing) await updateRole(role.id, body)
      else await createRole(body)
      toast.success(editing ? "Role updated" : "Role created")
      onSaved()
    } catch (err) {
      toast.error(err?.response?.data?.name?.[0] || err?.response?.data?.detail || "Failed to save role")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent className="max-h-[88vh] w-[95vw] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editing ? `Edit role, ${role.name}` : "New role"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="role-name">Name</Label>
          <Input id="role-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Grader" />
        </div>
        <div className="max-h-[50vh] space-y-4 overflow-y-auto pr-1">
          {Object.entries(groups).map(([g, items]) => (
            <div key={g}>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{g}</p>
              <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                {items.map((it) => {
                  const on = perms.has(it.code)
                  return (
                    <button
                      key={it.code}
                      type="button"
                      onClick={() => toggle(it.code)}
                      aria-pressed={on}
                      className={cn(
                        "flex min-h-[40px] items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors",
                        on ? "border-indigo bg-indigo/5" : "border-border hover:border-indigo/50",
                      )}
                    >
                      <span
                        className={cn(
                          "grid size-4 shrink-0 place-items-center rounded border",
                          on ? "border-indigo bg-primary text-primary-foreground" : "border-muted-foreground/40",
                        )}
                        aria-hidden="true"
                      >
                        {on && <Check className="size-3" />}
                      </span>
                      <span>{it.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
        <DialogFooter showCloseButton>
          <Button onClick={save} disabled={saving}>
            {saving ? "Saving…" : editing ? "Save role" : "Create role"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Assign a role to a member, optionally scoped to a top-level group.
function AssignDialog({ members, roles, classes, onClose, onSaved }) {
  const [userId, setUserId] = useState("")
  const [roleId, setRoleId] = useState("")
  const [scope, setScope] = useState(ORG_WIDE)
  const [saving, setSaving] = useState(false)

  async function save() {
    if (!userId || !roleId) {
      toast.error("Pick a member and a role")
      return
    }
    setSaving(true)
    try {
      await createRoleBinding({
        user: userId,
        role: roleId,
        scope_group: scope === ORG_WIDE ? null : Number(scope),
      })
      toast.success("Role assigned")
      onSaved()
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.response?.data?.user?.[0] || "Failed to assign role")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent className="max-h-[88vh] w-[95vw] max-w-xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Assign a role</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Member</Label>
            <Select value={userId} onValueChange={setUserId}>
              <SelectTrigger className="min-h-[40px] w-full"><SelectValue placeholder="Select a member…" /></SelectTrigger>
              <SelectContent>
                {members.map((m) => (
                  <SelectItem key={m.user_id} value={String(m.user_id)}>{m.email}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select value={roleId} onValueChange={setRoleId}>
              <SelectTrigger className="min-h-[40px] w-full"><SelectValue placeholder="Select a role…" /></SelectTrigger>
              <SelectContent>
                {roles.map((r) => (
                  <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Scope</Label>
            <Select value={scope} onValueChange={setScope}>
              <SelectTrigger className="min-h-[40px] w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ORG_WIDE}>Whole organization</SelectItem>
                {classes.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name} (+ its sub-groups)</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter showCloseButton>
          <Button onClick={save} disabled={saving || !userId || !roleId}>
            {saving ? "Assigning…" : "Assign role"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function OrgRoles() {
  const { activeOrg } = useOrg()
  const id = activeOrg?.id // org id (for the members endpoint)
  const [tab, setTab] = useState("roles")
  const [catalog, setCatalog] = useState([])
  const [roles, setRoles] = useState([])
  const [members, setMembers] = useState([])
  const [bindings, setBindings] = useState([])
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [roleDialog, setRoleDialog] = useState(null) // {} for new, {role} for edit
  const [assignOpen, setAssignOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cat, rs, bs, cls] = await Promise.all([
        getPermissionCatalog(),
        listRoles(),
        listRoleBindings(),
        listClasses({ parent: "none" }),
      ])
      setCatalog(cat)
      setRoles(rs.results ?? rs)
      setBindings(bs.results ?? bs)
      setClasses(cls.results ?? cls)
    } catch {
      toast.error("Failed to load roles")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // members come from the org endpoint (needs the org id from the URL)
  useEffect(() => {
    if (id) getMembers(id).then((d) => setMembers(d.results ?? d)).catch(() => {})
  }, [id])

  async function handleDeleteRole(role) {
    try {
      await deleteRole(role.id)
      toast.success("Role deleted")
      load()
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to delete role")
    }
  }

  async function handleRemoveBinding(b) {
    try {
      await deleteRoleBinding(b.id)
      toast.success("Role removed")
      load()
    } catch {
      toast.error("Failed to remove role")
    }
  }

  const scopeName = (gid) => classes.find((c) => c.id === gid)?.name

  useSubNav(ROLES_SECTIONS, tab, setTab, "Roles & permissions")

  return (
    <PageShell>
      <PageHeader
        title="Roles & permissions"
        description="Set what each role can do, then assign it to members."
        actions={<Button onClick={() => setRoleDialog({})}><Plus className="size-4" aria-hidden="true" /> New role</Button>}
      />

      {tab === "roles" && (
      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Roles</h2>
        {loading ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[72px] w-full rounded-xl" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {roles.map((r) => (
              <div key={r.id} className="rounded-xl border border-border bg-surface-1 p-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-4 shrink-0 text-indigo" aria-hidden="true" />
                  <p className="min-w-0 flex-1 truncate font-semibold">{r.name}</p>
                  {r.is_system && <Badge variant="neutral">System</Badge>}
                </div>
                <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                  {r.permissions.length} permission{r.permissions.length === 1 ? "" : "s"}
                </p>
                <div className="mt-3 flex items-center gap-1">
                  <Button variant="outline" size="sm" className="min-h-[36px] flex-1" onClick={() => setRoleDialog({ role: r })}>
                    {r.is_system ? "View permissions" : "Edit"}
                  </Button>
                  {!r.is_system && (
                    <Button variant="ghost" size="icon-sm" aria-label={`Delete ${r.name}`} onClick={() => handleDeleteRole(r)}>
                      <XIcon className="size-4" aria-hidden="true" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      )}

      {tab === "members" && (
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Member roles</h2>
          <Button variant="outline" size="sm" className="min-h-[40px]" onClick={() => setAssignOpen(true)}>
            <Plus className="size-4" aria-hidden="true" /> Assign role
          </Button>
        </div>
        {bindings.length === 0 ? (
          <p className="text-sm text-muted-foreground">No role assignments yet. Admins always have full access.</p>
        ) : (
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
            {bindings.map((b) => (
              <li key={b.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{b.user_email}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <Badge variant="info">{b.role_name}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {b.scope_group ? `${scopeName(b.scope_group) ?? "a class"} + sub-groups` : "Whole organization"}
                    </span>
                  </div>
                </div>
                <Button variant="ghost" size="icon-sm" aria-label="Remove role" onClick={() => handleRemoveBinding(b)}>
                  <XIcon className="size-4" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
      )}

      {roleDialog && (
        <RoleDialog
          role={roleDialog.role}
          catalog={catalog}
          onClose={() => setRoleDialog(null)}
          onSaved={() => { setRoleDialog(null); load() }}
        />
      )}
      {assignOpen && (
        <AssignDialog
          members={members}
          roles={roles}
          classes={classes}
          onClose={() => setAssignOpen(false)}
          onSaved={() => { setAssignOpen(false); load() }}
        />
      )}
    </PageShell>
  )
}
