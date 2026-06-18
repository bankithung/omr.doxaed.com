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
import { listRosters, generateSheets, mediaUrl, downloadAuthedBlob } from "@/api/omr"
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
import { DetailHeaderSkeleton, ListSkeleton } from "@/components/ui/list-skeletons"
import { DataList } from "@/components/ui/data-list"
import { ActionMenu } from "@/components/ui/action-menu"
import { Badge } from "@/components/ui/badge"
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

function GenerateSheetsDialog({ test, open, onOpenChange }) {
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
    listRosters()
      .then((data) => setRosters(data.results ?? data))
      .catch(() => toast.error("Failed to load rosters"))
  }, [open])

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
                No rosters found.{" "}
                <Link to="/rosters" className="underline hover:text-foreground">
                  Create one first.
                </Link>
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
            <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-950/30">
              <p className="mb-2 text-sm font-medium text-green-800 dark:text-green-300">
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
    <div className="mb-8 rounded-xl border p-4">
      <p className="text-sm font-semibold">Subjects</p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        Define subjects for this class to pick them quickly when creating tests.
      </p>

      <form onSubmit={handleAdd} className="mt-3 flex items-center gap-2">
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

      <div className="mt-3">
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading subjects…</p>
        ) : subjects.length === 0 ? (
          <p className="text-sm text-muted-foreground">No subjects yet.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {subjects.map((s) => (
              <li
                key={s.id}
                className="flex items-center gap-1.5 rounded-full border border-border bg-background py-1 pl-3 pr-1.5 text-sm"
              >
                <span>{s.name}</span>
                <button
                  type="button"
                  onClick={() => setDeleteTarget(s)}
                  aria-label={`Remove subject ${s.name}`}
                  className="flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-destructive transition-colors"
                >
                  <XIcon className="size-3.5" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

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

// ─── Main TestList screen ──────────────────────────

export default function TestList() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [classGroup, setClassGroup] = useState(null)
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retestingId, setRetestingId] = useState(null)
  const [generateTest, setGenerateTest] = useState(null)

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
        <span className="text-muted-foreground">#{test.attempt_number}</span>
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
      <div className="mx-auto max-w-4xl px-4 py-8 space-y-6">
        <DetailHeaderSkeleton />
        <ListSkeleton rows={4} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <ErrorState
          title="Couldn't load class data"
          description="Something went wrong while loading this class and its tests."
          onRetry={fetchData}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Breadcrumb */}
      <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/classes" className="hover:text-foreground hover:underline">
          Classes
        </Link>
        <span>/</span>
        <span>{classGroup?.name ?? "Class"}</span>
      </div>

      <PageHeader
        className="mb-6"
        title={classGroup?.name ?? "Class"}
        description={classGroup?.description}
        actions={
          <Button onClick={() => navigate(`/classes/${id}/tests/new`)}>
            Create test
          </Button>
        }
      />

      {/* Subjects (Phase 5D) */}
      <SubjectsSection classId={id} />

      {tests.length === 0 ? (
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
        <DataList
          columns={columns}
          rows={tests}
          getRowKey={(test) => test.id}
        />
      )}

      {/* Generate sheets dialog */}
      {generateTest && (
        <GenerateSheetsDialog
          test={generateTest}
          open={Boolean(generateTest)}
          onOpenChange={(v) => { if (!v) setGenerateTest(null) }}
        />
      )}
    </div>
  )
}
