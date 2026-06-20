import { useEffect, useState, useCallback } from "react"
import { useNavigate, Link } from "react-router-dom"
import { toast } from "sonner"
import {
  ScanLine,
  BarChart2,
  ClipboardList,
  RefreshCw,
  CheckCircle,
  FileText,
  Search,
  X as XIcon,
} from "lucide-react"
import { listTests, retest, listClasses } from "@/api/assessments"
import { listSubjects, createSubject, deleteSubject } from "@/api/subjects"
import { listRosters, createRoster } from "@/api/omr"
import {
  getMembers,
  listClassGrants,
  createClassGrant,
  updateClassGrant,
  deleteClassGrant,
} from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { useClass } from "@/features/class/useClass"
import { childKindLabel } from "@/features/class/typePresets"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/skeletons"
import { DataTable } from "@/components/ui/DataTable"
import { ActionMenu } from "@/components/ui/action-menu"
import { Badge } from "@/components/ui/badge"

// ─── Status badge ─────────────────────────────────

const STATUS_VARIANT = {
  draft: "warning",
  ready: "success",
  closed: "neutral",
}

const STATUS_LABELS = {
  draft: "Draft",
  ready: "Ready",
  closed: "Closed",
}

export function StatusBadge({ status }) {
  return (
    <Badge variant={STATUS_VARIANT[status] ?? "neutral"}>
      {STATUS_LABELS[status] ?? status}
    </Badge>
  )
}

// ─── Test row actions ──────────────────────────────
//
// E2E SAFETY: "Generate sheets" stays a DIRECT visible Button (not in a menu)
// for tests that haven't been generated yet (status = draft/ready with no sheets).
// Scan / Results / Review / Analytics / Retest go into the ActionMenu overflow.

export function TestActions({ test, onRetest, retestingId }) {
  const navigate = useNavigate()

  const menuItems = [
    {
      label: "Scan",
      icon: <ScanLine className="size-4" />,
      onSelect: () => navigate(`/tests/${test.id}/scan`),
    },
    {
      label: "Results",
      icon: <ClipboardList className="size-4" />,
      onSelect: () => navigate(`/tests/${test.id}/results`),
    },
    {
      label: "Review",
      icon: <CheckCircle className="size-4" />,
      onSelect: () => navigate(`/tests/${test.id}/review`),
    },
    {
      label: "Analytics",
      icon: <BarChart2 className="size-4" />,
      onSelect: () => navigate(`/tests/${test.id}/analytics`),
    },
    {
      label: retestingId === test.id ? "Creating…" : "Retest",
      icon: <RefreshCw className="size-4" />,
      onSelect: () => onRetest(test.id),
      disabled: retestingId === test.id,
      separator: true,
    },
  ]

  return (
    <div className="flex items-center justify-end gap-2">
      {/* Generate sheets — direct button → dedicated Generate & Print page */}
      <Button
        variant="outline"
        size="sm"
        className="min-h-[40px]"
        onClick={() => navigate(`/tests/${test.id}/sheets`)}
      >
        Generate sheets
      </Button>
      {/* Overflow menu — Scan / Results / Review / Analytics / Retest */}
      <ActionMenu items={menuItems} triggerLabel="More test actions" />
    </div>
  )
}

// ─── Subjects section (per class) ──────────────────
//
// Lists subjects for the class, supports inline add + custom-confirm delete.
// Surfaces view-only (403) errors inline via toast — never alert.

export function SubjectsSection({ classId }) {
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState("")
  const [adding, setAdding] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const fetchSubjects = useCallback(async () => {
    try {
      const data = await listSubjects(classId)
      setSubjects(data.results ?? data)
    } catch {
      toast.error("Failed to load subjects")
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    fetchSubjects()
  }, [fetchSubjects])

  async function handleAdd(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Subject name is required")
      return
    }
    setAdding(true)
    try {
      await createSubject({ class_group: classId, name: name.trim() })
      setName("")
      toast.success("Subject added")
      fetchSubjects()
    } catch (err) {
      const msg =
        err?.response?.data?.name?.[0] ||
        err?.response?.data?.detail ||
        "Failed to add subject"
      toast.error(msg)
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteSubject(deleteTarget.id)
      toast.success("Subject removed")
      setDeleteTarget(null)
      fetchSubjects()
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to remove subject"
      toast.error(msg)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Define subjects for this class to pick them quickly when creating tests.
      </p>
      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <Input
          placeholder="e.g. Mathematics"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1"
          aria-label="New subject name"
        />
        <Button type="submit" size="sm" className="min-h-[40px]" disabled={adding}>
          {adding ? "Adding…" : "Add subject"}
        </Button>
      </form>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading subjects…</p>
      ) : subjects.length === 0 ? (
        <p className="text-sm text-muted-foreground">No subjects yet.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {subjects.map((s) => (
            <li
              key={s.id}
              className="flex items-center gap-1.5 rounded-full border border-border bg-surface-2 py-1 pl-3 pr-1.5 text-sm"
            >
              <span>{s.name}</span>
              <button
                type="button"
                onClick={() => setDeleteTarget(s)}
                aria-label={`Remove subject ${s.name}`}
                className="flex size-6 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-destructive"
              >
                <XIcon className="size-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Delete confirm (custom — never window.confirm) */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => !deleting && !o && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove subject</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Remove <strong>{deleteTarget?.name}</strong> from this class? Existing tests keep
            their subject text.
          </p>
          <DialogFooter showCloseButton>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Removing…" : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Rosters section (per class) ───────────────────
//
// The class's student lists. Add a roster (stamped with this class_group) then
// manage its students on the roster page. Rosters created here belong to the
// class, so the Generate-sheets picker shows them automatically.

export function RostersSection({ classId }) {
  const [rosters, setRosters] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState("")
  const [adding, setAdding] = useState(false)

  const fetchRosters = useCallback(async () => {
    try {
      const data = await listRosters({ class_group: classId })
      setRosters(data.results ?? data)
    } catch {
      toast.error("Failed to load rosters")
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    fetchRosters()
  }, [fetchRosters])

  async function handleAdd(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Roster name is required")
      return
    }
    setAdding(true)
    try {
      await createRoster({ name: name.trim(), class_group: classId })
      setName("")
      toast.success("Roster added")
      fetchRosters()
    } catch (err) {
      const msg =
        err?.response?.data?.name?.[0] ||
        err?.response?.data?.detail ||
        "Failed to add roster"
      toast.error(msg)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        The student lists for this class. Add a roster, then add students (or a
        roll count) to it — generated OMR sheets use this class's rosters.
      </p>
      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <Input
          placeholder="e.g. Section A"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1"
          aria-label="New roster name"
        />
        <Button type="submit" size="sm" className="min-h-[40px]" disabled={adding}>
          {adding ? "Adding…" : "Add roster"}
        </Button>
      </form>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading rosters…</p>
      ) : rosters.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No rosters yet. Add one to manage this class's students.
        </p>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
          {rosters.map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between gap-3 px-3 py-2.5"
            >
              <div className="min-w-0">
                <Link
                  to={`/rosters/${r.id}`}
                  className="font-medium hover:text-primary hover:underline"
                >
                  {r.name}
                </Link>
                <span className="ml-2 text-sm text-muted-foreground tabular">
                  {r.student_count ?? r.students_count ?? 0} students
                </span>
              </div>
              <Button variant="outline" size="sm" asChild className="min-h-[40px]">
                <Link to={`/rosters/${r.id}`}>Manage students</Link>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ─── Narrow-subjects dialog ────────────────────────
//
// Picks which of the class's subjects a teacher may access. Selecting NONE means
// "all subjects" (all_subjects=true); selecting some narrows to those ids.

function NarrowSubjectsDialog({ grant, subjects, onClose, onSaved }) {
  const [selected, setSelected] = useState(() => new Set(grant.subjects ?? []))
  const [saving, setSaving] = useState(false)

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSave() {
    setSaving(true)
    try {
      const ids = [...selected]
      // No subjects chosen → grant the whole class (all_subjects=true).
      const body = ids.length
        ? { all_subjects: false, subjects: ids }
        : { all_subjects: true, subjects: [] }
      await updateClassGrant(grant.id, body)
      toast.success("Access updated")
      onSaved()
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to update access")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Subjects for {grant.user_email}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Choose which subjects this teacher can access in this class. Select none
          to grant <span className="font-medium text-foreground">all subjects</span>.
        </p>
        {subjects.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            This class has no subjects yet — add some in the Subjects tab to narrow
            access.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {subjects.map((s) => {
              const on = selected.has(s.id)
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => toggle(s.id)}
                  aria-pressed={on}
                  className={cn(
                    "min-h-[40px] rounded-full border px-4 text-sm font-medium transition-colors",
                    on
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-surface-2 text-foreground hover:border-primary/50",
                  )}
                >
                  {s.name}
                </button>
              )
            })}
          </div>
        )}
        <DialogFooter showCloseButton>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save access"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Access section (per class, ADMIN ONLY) ────────
//
// An org admin grants teachers (members) access to THIS class. Grants default to
// all subjects; the admin can narrow to specific ones. Enforcement lives in the
// API (common/scope.py) — a member without a grant never sees the class. This UI
// only manages the grant rows and is rendered solely for admins.

export function AccessSection({ classId }) {
  const { activeOrgId } = useOrg() ?? {}
  const [grants, setGrants] = useState([])
  const [members, setMembers] = useState([])
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [addUserId, setAddUserId] = useState("")
  const [adding, setAdding] = useState(false)
  const [removeTarget, setRemoveTarget] = useState(null)
  const [removing, setRemoving] = useState(false)
  const [narrowTarget, setNarrowTarget] = useState(null)
  const cls = useClass(classId)
  // Subjects are class-wide — read the PARENT class's when this is a section.
  const subjectsClassId = cls?.parent ?? classId

  const fetchAll = useCallback(async () => {
    try {
      const [grantData, memberData, subjectData] = await Promise.all([
        listClassGrants(classId),
        activeOrgId ? getMembers(activeOrgId) : Promise.resolve([]),
        listSubjects(subjectsClassId),
      ])
      setGrants(grantData.results ?? grantData)
      setMembers(memberData.results ?? memberData)
      setSubjects(subjectData.results ?? subjectData)
    } catch {
      toast.error("Failed to load access settings")
    } finally {
      setLoading(false)
    }
  }, [classId, activeOrgId, subjectsClassId])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // Addable = active members, not admins (they already have full access), not
  // already granted.
  const grantedUserIds = new Set(grants.map((g) => g.user))
  const addable = members.filter(
    (m) => m.status === "active" && m.role !== "admin" && !grantedUserIds.has(m.user_id),
  )

  async function handleAdd() {
    if (!addUserId) return
    setAdding(true)
    try {
      await createClassGrant({
        user: addUserId,
        class_group: classId,
        all_subjects: true,
      })
      setAddUserId("")
      toast.success("Teacher granted access")
      fetchAll()
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to grant access")
    } finally {
      setAdding(false)
    }
  }

  async function handleRemove() {
    if (!removeTarget) return
    setRemoving(true)
    try {
      await deleteClassGrant(removeTarget.id)
      toast.success("Access removed")
      setRemoveTarget(null)
      fetchAll()
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to remove access")
    } finally {
      setRemoving(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading access settings…</p>
  }

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Grant teachers access to this class. A grant covers all subjects by default
        — use <span className="font-medium text-foreground">Subjects</span> on a row
        to limit a teacher to specific ones. Teachers without a grant can't see this
        class; admins always have full access.
      </p>

      {/* Add a teacher */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Select value={addUserId} onValueChange={setAddUserId} disabled={addable.length === 0}>
          <SelectTrigger className="w-full sm:max-w-xs">
            <SelectValue
              placeholder={addable.length ? "Select a teacher…" : "No teachers to add"}
            />
          </SelectTrigger>
          <SelectContent>
            {addable.map((m) => (
              <SelectItem key={m.user_id} value={String(m.user_id)}>
                {m.email}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          onClick={handleAdd}
          size="sm"
          className="min-h-[40px]"
          disabled={!addUserId || adding}
        >
          {adding ? "Granting…" : "Grant access"}
        </Button>
      </div>

      {/* Current grants */}
      {grants.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No teachers have access yet.
        </p>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
          {grants.map((g) => (
            <li
              key={g.id}
              className="flex flex-col gap-2 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{g.user_email}</p>
                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                  {g.all_subjects ? (
                    <Badge variant="success">All subjects</Badge>
                  ) : g.subject_names.length ? (
                    g.subject_names.map((n) => (
                      <Badge key={n} variant="neutral">
                        {n}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="warning">No subjects</Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-[40px]"
                  onClick={() => setNarrowTarget(g)}
                >
                  Subjects
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-[40px]"
                  onClick={() => setRemoveTarget(g)}
                  aria-label={`Remove access for ${g.user_email}`}
                >
                  <XIcon className="size-4" aria-hidden="true" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Narrow subjects dialog */}
      {narrowTarget && (
        <NarrowSubjectsDialog
          grant={narrowTarget}
          subjects={subjects}
          onClose={() => setNarrowTarget(null)}
          onSaved={() => {
            setNarrowTarget(null)
            fetchAll()
          }}
        />
      )}

      {/* Remove confirm (custom — never window.confirm) */}
      <Dialog
        open={!!removeTarget}
        onOpenChange={(o) => !removing && !o && setRemoveTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove access</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Remove <strong>{removeTarget?.user_email}</strong>'s access to this class?
            They'll no longer see it or its tests.
          </p>
          <DialogFooter showCloseButton>
            <Button variant="destructive" onClick={handleRemove} disabled={removing}>
              {removing ? "Removing…" : "Remove access"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Exams section (per class) ─────────────────────
//
// The class's exams table. Rendered by the ClassExams workspace page; the class
// header + "New exam" action live on that page.

export function ExamsSection({ classId }) {
  const navigate = useNavigate()
  const cls = useClass(classId)
  const { activeOrg } = useOrg() ?? {}
  const childLabel = childKindLabel(activeOrg?.type, cls?.kind_label)
  const lower = childLabel.toLowerCase()
  const [tests, setTests] = useState([])
  const [sections, setSections] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retestingId, setRetestingId] = useState(null)
  const [filter, setFilter] = useState("all")
  const [query, setQuery] = useState("")

  // Exams can live on the class itself OR on any of its sections (the wizard lets
  // you pick). Pull them all so the class page is the single place to see them.
  const fetchTests = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const secD = await listClasses({ parent: classId })
      const secs = secD.results ?? secD
      setSections(secs)
      const groups = [
        { id: classId, label: null },
        ...secs.map((s) => ({ id: s.id, label: s.name })),
      ]
      const perGroup = await Promise.all(
        groups.map(async (g) => {
          const data = await listTests(g.id)
          const rows = data.results ?? data
          return rows.map((t) => ({ ...t, _section: g.label, _gid: String(g.id) }))
        }),
      )
      setTests(perGroup.flat())
    } catch {
      setError(true)
      toast.error("Failed to load exams")
    } finally {
      setLoading(false)
    }
  }, [classId])

  useEffect(() => {
    fetchTests()
  }, [fetchTests])

  async function handleRetest(testId) {
    setRetestingId(testId)
    try {
      const newTest = await retest(testId)
      toast.success(`Retest created: attempt #${newTest.attempt_number}`)
      fetchTests()
    } catch {
      toast.error("Failed to create retest")
    } finally {
      setRetestingId(null)
    }
  }

  const hasSections = sections.length > 0
  const q = query.trim().toLowerCase()
  // Section filter + free-text search, newest first. Sort by created_at, NOT id
  // (ids are UUID strings now — id arithmetic no longer orders by recency).
  const filtered = tests
    .filter((t) => filter === "all" || t._gid === filter)
    .filter((t) => !q || t.title?.toLowerCase().includes(q) || t.subject?.toLowerCase().includes(q))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))

  const columns = [
    {
      key: "title",
      header: "Title",
      cell: (test) => (
        <Link to={`/tests/${test.id}`} className="font-medium hover:text-primary hover:underline">
          {test.title}
        </Link>
      ),
    },
    {
      key: "subject",
      header: "Subject",
      cell: (test) =>
        test.subject ? (
          <span className="text-muted-foreground">{test.subject}</span>
        ) : (
          <span className="italic text-muted-foreground">—</span>
        ),
    },
    ...(hasSections
      ? [
          {
            key: "section",
            header: childLabel,
            cell: (test) =>
              test._section ? (
                <Badge variant="neutral">{test._section}</Badge>
              ) : (
                <span className="text-xs text-muted-foreground">Whole class</span>
              ),
          },
        ]
      : []),
    {
      key: "status",
      header: "Status",
      cell: (test) => <StatusBadge status={test.status} />,
    },
    {
      key: "attempt",
      header: "Attempt",
      cell: (test) => (
        <span className="text-muted-foreground tabular">#{test.attempt_number}</span>
      ),
    },
    {
      key: "created",
      header: "Created",
      cell: (test) => (
        <span className="text-xs text-muted-foreground tabular-nums">
          {test.created_at
            ? new Date(test.created_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })
            : "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      mobileLabel: "",
      cell: (test) => (
        <TestActions test={test} onRetest={handleRetest} retestingId={retestingId} />
      ),
      className: "text-right",
    },
  ]

  if (loading) return <TableSkeleton rows={4} />

  if (error) {
    return (
      <ErrorState
        title="Couldn't load exams"
        description="Something went wrong while loading this class's exams."
        onRetry={fetchTests}
      />
    )
  }

  if (tests.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No exams yet"
        description="Create the first exam for this class."
        action={
          <Button onClick={() => navigate(`/classes/${classId}/tests/new`)}>New exam</Button>
        }
      />
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            placeholder="Search exams…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
            aria-label="Search exams"
          />
        </div>
        {hasSections && (
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="min-h-[40px] w-full sm:w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All {lower}s</SelectItem>
              <SelectItem value={String(classId)}>Whole class</SelectItem>
              {sections.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">
          {filtered.length} exam{filtered.length === 1 ? "" : "s"}
        </span>
      </div>
      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No exams match your filters.</p>
      ) : (
        <DataTable columns={columns} rows={filtered} getRowKey={(test) => test.id} />
      )}
    </div>
  )
}
