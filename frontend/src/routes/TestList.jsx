import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { toast } from "sonner"
import {
  ScanLine,
  BarChart2,
  ClipboardList,
  RefreshCw,
  CheckCircle,
  FileText,
  X as XIcon,
} from "lucide-react"
import { getClass, listTests, retest } from "@/api/assessments"
import { listSubjects, createSubject, deleteSubject } from "@/api/subjects"
import { listRosters, createRoster, generateSheets, mediaUrl, downloadAuthedBlob } from "@/api/omr"
import {
  getMembers,
  listClassGrants,
  createClassGrant,
  updateClassGrant,
  deleteClassGrant,
} from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
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
import { Skeleton } from "@/components/ui/skeleton"
import { DataTable } from "@/components/ui/DataTable"
import { ActionMenu } from "@/components/ui/action-menu"
import { Badge } from "@/components/ui/badge"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

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

function StatusBadge({ status }) {
  return (
    <Badge variant={STATUS_VARIANT[status] ?? "neutral"}>
      {STATUS_LABELS[status] ?? status}
    </Badge>
  )
}

// ─── Generate Sheets Dialog ────────────────────────

function GenerateSheetsDialog({ test, classId, open, onOpenChange }) {
  const [rosters, setRosters] = useState([])
  const [rosterId, setRosterId] = useState("")
  const [shuffleQuestions, setShuffleQuestions] = useState(true)
  const [shuffleOptions, setShuffleOptions] = useState(true)
  const [loading, setLoading] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState(null)
  // batch_paper_url is an AUTHED API endpoint (not a /media/ link)
  const [paperBatchUrl, setPaperBatchUrl] = useState(null)
  const [downloadingPaper, setDownloadingPaper] = useState(false)

  useEffect(() => {
    if (!open) return
    setDownloadUrl(null)
    setPaperBatchUrl(null)
    setRosterId("")
    listRosters({ class_group: classId })
      .then((data) => setRosters(data.results ?? data))
      .catch(() => toast.error("Failed to load rosters"))
  }, [open, classId])

  async function handleGenerate() {
    if (!rosterId) {
      toast.error("Please select a roster")
      return
    }
    setLoading(true)
    setDownloadUrl(null)
    setPaperBatchUrl(null)
    try {
      const resp = await generateSheets({
        test: test.id,
        roster: Number(rosterId),
        shuffle_questions: shuffleQuestions,
        shuffle_options: shuffleOptions,
      })
      const url = mediaUrl(resp.batch_pdf_url)
      setDownloadUrl(url)
      // batch_paper_url present when shuffle was on → question papers were emitted
      if (resp.batch_paper_url) {
        setPaperBatchUrl(resp.batch_paper_url)
      }
      toast.success(`Generated ${resp.count ?? resp.sheets?.length ?? ""} sheet(s)`)
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to generate sheets"
      toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  async function handleDownloadPapers() {
    if (!paperBatchUrl) return
    setDownloadingPaper(true)
    try {
      await downloadAuthedBlob(paperBatchUrl, "question-papers.pdf")
    } catch {
      toast.error("Failed to download question papers")
    } finally {
      setDownloadingPaper(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Generate OMR sheets</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Test: <span className="font-medium text-foreground">{test.title}</span>
        </p>

        <div className="flex flex-col gap-4">
          {/* Roster picker */}
          <div className="flex flex-col gap-1.5">
            <Label>Roster</Label>
            {rosters.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                This class has no rosters yet. Add one in the{" "}
                <span className="font-medium text-foreground">Rosters</span> section
                of this class, then come back to generate.
              </p>
            ) : (
              <Select value={rosterId} onValueChange={setRosterId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a roster…" />
                </SelectTrigger>
                <SelectContent>
                  {rosters.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Shuffle toggles */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="shuffle-questions" className="cursor-pointer">
                Shuffle questions
              </Label>
              <Switch
                id="shuffle-questions"
                checked={shuffleQuestions}
                onCheckedChange={setShuffleQuestions}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="shuffle-options" className="cursor-pointer">
                Shuffle options
              </Label>
              <Switch
                id="shuffle-options"
                checked={shuffleOptions}
                onCheckedChange={setShuffleOptions}
              />
            </div>
          </div>

          {/* Download links after success */}
          {downloadUrl && (
            <div className="rounded-lg border border-[var(--color-success)]/40 bg-[color-mix(in_oklch,var(--color-success)_10%,transparent)] p-3">
              <p className="mb-2 text-sm font-medium text-[var(--color-success)]">
                Sheets generated successfully!
              </p>
              <div className="flex flex-wrap gap-2">
                <Button asChild size="sm" variant="outline">
                  <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
                    Download sheets PDF
                  </a>
                </Button>
                {paperBatchUrl && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleDownloadPapers}
                    disabled={downloadingPaper}
                  >
                    {downloadingPaper ? "Downloading…" : "Download question papers"}
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={handleGenerate}
            disabled={loading || !rosterId}
          >
            {loading ? "Generating…" : "Generate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Test row actions ──────────────────────────────
//
// E2E SAFETY: "Generate sheets" stays a DIRECT visible Button (not in a menu)
// for tests that haven't been generated yet (status = draft/ready with no sheets).
// Scan / Results / Review / Analytics / Retest go into the ActionMenu overflow.

function TestActions({ test, onGenerate, onRetest, retestingId }) {
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
      {/* Generate sheets — direct button, always visible */}
      <Button
        variant="outline"
        size="sm"
        className="min-h-[40px]"
        onClick={() => onGenerate(test)}
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

function SubjectsSection({ classId }) {
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
      await createSubject({ class_group: Number(classId), name: name.trim() })
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

function RostersSection({ classId }) {
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
      await createRoster({ name: name.trim(), class_group: Number(classId) })
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

function AccessSection({ classId }) {
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

  const fetchAll = useCallback(async () => {
    try {
      const [grantData, memberData, subjectData] = await Promise.all([
        listClassGrants(classId),
        activeOrgId ? getMembers(activeOrgId) : Promise.resolve([]),
        listSubjects(classId),
      ])
      setGrants(grantData.results ?? grantData)
      setMembers(memberData.results ?? memberData)
      setSubjects(subjectData.results ?? subjectData)
    } catch {
      toast.error("Failed to load access settings")
    } finally {
      setLoading(false)
    }
  }, [classId, activeOrgId])

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
        user: Number(addUserId),
        class_group: Number(classId),
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

// ─── Main TestList screen ──────────────────────────

const CLASS_TABS = [
  { key: "tests", label: "Tests" },
  { key: "rosters", label: "Rosters" },
  { key: "subjects", label: "Subjects" },
]

export default function TestList() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { activeOrg } = useOrg() ?? {}
  const isAdmin = activeOrg?.role === "admin"
  const tabs = isAdmin
    ? [...CLASS_TABS, { key: "access", label: "Teacher access" }]
    : CLASS_TABS
  const [classGroup, setClassGroup] = useState(null)
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retestingId, setRetestingId] = useState(null)
  const [generateTest, setGenerateTest] = useState(null)
  const [tab, setTab] = useState("tests")

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [cls, testsData] = await Promise.all([getClass(id), listTests(id)])
      setClassGroup(cls)
      setTests(testsData.results ?? testsData)
    } catch {
      setError(true)
      toast.error("Failed to load class data")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  async function handleRetest(testId) {
    setRetestingId(testId)
    try {
      const newTest = await retest(testId)
      toast.success(`Retest created: attempt #${newTest.attempt_number}`)
      fetchData()
    } catch {
      toast.error("Failed to create retest")
    } finally {
      setRetestingId(null)
    }
  }

  const columns = [
    {
      key: "title",
      header: "Title",
      cell: (test) => <span className="font-medium">{test.title}</span>,
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
      key: "actions",
      header: "",
      mobileLabel: "",
      cell: (test) => (
        <TestActions
          test={test}
          onGenerate={setGenerateTest}
          onRetest={handleRetest}
          retestingId={retestingId}
        />
      ),
      className: "text-right",
    },
  ]

  if (loading) {
    return (
      <PageShell>
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-32 w-full rounded-lg" />
        <TableSkeleton rows={4} />
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Couldn't load class data"
          description="Something went wrong while loading this class and its tests."
          onRetry={fetchData}
        />
      </PageShell>
    )
  }

  return (
    <PageShell>
      <PageHeader
        title={classGroup?.name ?? "Class"}
        description={classGroup?.description}
        actions={
          <Button onClick={() => navigate(`/classes/${id}/tests/new`)}>
            Create test
          </Button>
        }
      />

      {/* Tabs — Tests / Rosters / Subjects (refined, single home for the class) */}
      <div>
        <div
          role="tablist"
          aria-label="Class sections"
          className="flex gap-1 overflow-x-auto border-b border-border"
        >
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "relative -mb-px min-h-[40px] whitespace-nowrap border-b-2 px-3.5 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                tab === t.key
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div role="tabpanel" className="pt-5">
          {tab === "tests" &&
            (tests.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No tests yet"
                description="Create the first test for this class."
                action={
                  <Button onClick={() => navigate(`/classes/${id}/tests/new`)}>
                    Create test
                  </Button>
                }
              />
            ) : (
              <DataTable columns={columns} rows={tests} getRowKey={(test) => test.id} />
            ))}
          {tab === "rosters" && <RostersSection classId={id} />}
          {tab === "subjects" && <SubjectsSection classId={id} />}
          {tab === "access" && isAdmin && <AccessSection classId={id} />}
        </div>
      </div>

      {/* Generate sheets dialog */}
      {generateTest && (
        <GenerateSheetsDialog
          test={generateTest}
          classId={id}
          open={Boolean(generateTest)}
          onOpenChange={(v) => { if (!v) setGenerateTest(null) }}
        />
      )}
    </PageShell>
  )
}
