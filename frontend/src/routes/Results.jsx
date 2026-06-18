import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { ChevronUp, ChevronDown, Check, X, AlertTriangle, ClipboardListIcon } from "lucide-react"
import { listResults } from "@/api/scan"
import { getPublishSettings, setPublishSettings, downloadBulkReportCards } from "@/api/analytics"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/ui/page-header"
import { Breadcrumb } from "@/components/ui/breadcrumb"
import { TestProgressRail } from "@/components/ui/test-progress-rail"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/list-skeletons"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

// ─── Badges ───────────────────────────────────────

function NeedsReviewBadge() {
  return <Badge variant="warning">Needs review</Badge>
}

function ScoreBadge({ score, maxScore }) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0
  const variant = pct >= 70 ? "success" : pct >= 40 ? "warning" : "error"
  return <Badge variant={variant}>{score}/{maxScore}</Badge>
}

// ─── Per-question response table (shared) ─────────

function QuestionResponseRow({ resp }) {
  return (
    <tr className="border-t border-border/40 text-xs">
      <td className="py-1 pl-8 pr-2 text-muted-foreground">
        Q{resp.q_pos ?? resp.question}
      </td>
      <td className="px-2 py-1">
        {resp.marked_options?.length > 0 ? (
          resp.marked_options.join(", ")
        ) : (
          <span className="italic text-muted-foreground">blank</span>
        )}
      </td>
      <td className="px-2 py-1">
        {resp.flagged ? (
          <span className="inline-flex items-center gap-1 text-[var(--color-warning)]">
            <AlertTriangle className="size-3" aria-hidden="true" />
            flagged
          </span>
        ) : resp.is_correct ? (
          <Check className="size-3.5 text-[var(--color-success)]" aria-label="Correct" />
        ) : (
          <X className="size-3.5 text-[var(--color-error)]" aria-label="Incorrect" />
        )}
      </td>
    </tr>
  )
}

function ResponsesTable({ responses }) {
  if (responses.length === 0) {
    return (
      <p className="py-2 pl-4 text-xs text-muted-foreground">
        No per-question responses recorded.
      </p>
    )
  }
  return (
    <table className="w-full">
      <thead>
        <tr className="text-xs text-muted-foreground">
          <th className="py-1 pl-8 pr-2 text-left font-normal">Q</th>
          <th className="px-2 py-1 text-left font-normal">Marked</th>
          <th className="px-2 py-1 text-left font-normal">Result</th>
        </tr>
      </thead>
      <tbody>
        {responses.map((r, i) => (
          <QuestionResponseRow key={r.id ?? i} resp={r} />
        ))}
      </tbody>
    </table>
  )
}

// ─── Desktop table row ─────────────────────────────

function StudentResultRow({ result, testId }) {
  const [expanded, setExpanded] = useState(false)
  const responses = result.responses ?? result.question_responses ?? []
  const studentId = result.student?.id ?? result.student

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={() => setExpanded((v) => !v)}
      >
        <TableCell className="font-mono text-sm">
          {result.student_roll ?? result.student?.roll_number ?? result.omr_sheet ?? "—"}
        </TableCell>
        <TableCell>
          {result.student_name ?? result.student?.name ?? result.student?.full_name ?? "—"}
        </TableCell>
        <TableCell>
          <ScoreBadge score={result.score ?? 0} maxScore={result.max_score ?? 0} />
        </TableCell>
        <TableCell className="text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-0.5 text-[var(--color-success)]">
            <Check className="size-3" aria-hidden="true" />
            {result.correct_count ?? 0}
          </span>
          {" / "}
          <span className="inline-flex items-center gap-0.5 text-[var(--color-error)]">
            <X className="size-3" aria-hidden="true" />
            {result.wrong_count ?? 0}
          </span>
          {" / "}
          <span>{result.blank_count ?? 0}</span>
        </TableCell>
        <TableCell>
          {result.needs_review ? <NeedsReviewBadge /> : null}
        </TableCell>
        <TableCell
          className="text-right text-xs text-muted-foreground"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-end gap-2">
            {studentId != null && (
              <Link
                to={`/tests/${testId}/students/${studentId}`}
                className="text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Detail
              </Link>
            )}
            <button
              type="button"
              aria-label={expanded ? "Collapse responses" : "Expand responses"}
              className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded text-muted-foreground hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded((v) => !v)
              }}
            >
              {expanded ? (
                <ChevronUp className="size-4" aria-hidden="true" />
              ) : (
                <ChevronDown className="size-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </TableCell>
      </TableRow>

      {expanded && (
        <TableRow className="bg-muted/20">
          <TableCell colSpan={6} className="p-0">
            <ResponsesTable responses={responses} />
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

// ─── Mobile result card ────────────────────────────

function StudentResultCard({ result, testId }) {
  const [expanded, setExpanded] = useState(false)
  const responses = result.responses ?? result.question_responses ?? []
  const studentId = result.student?.id ?? result.student
  const roll =
    result.student_roll ?? result.student?.roll_number ?? result.omr_sheet ?? "—"
  const name =
    result.student_name ?? result.student?.name ?? result.student?.full_name ?? "—"

  return (
    <div className="rounded-xl border bg-card shadow-sm">
      {/* Card header — tap to expand */}
      <button
        type="button"
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-medium">Roll: {roll}</span>
            <ScoreBadge
              score={result.score ?? 0}
              maxScore={result.max_score ?? 0}
            />
            {result.needs_review && <NeedsReviewBadge />}
          </div>
          <p className="mt-0.5 truncate text-sm text-muted-foreground">{name}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            <span className="text-[var(--color-success)]">
              {result.correct_count ?? 0} correct
            </span>
            {" · "}
            <span className="text-[var(--color-error)]">
              {result.wrong_count ?? 0} wrong
            </span>
            {" · "}
            {result.blank_count ?? 0} blank
          </p>
        </div>
        <span className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true">
          {expanded ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </span>
      </button>

      {/* Expanded per-question detail */}
      {expanded && (
        <div className="border-t">
          <div className="overflow-x-auto">
            <ResponsesTable responses={responses} />
          </div>
          {studentId != null && (
            <div className="border-t px-4 py-2">
              <Link
                to={`/tests/${testId}/students/${studentId}`}
                className="text-sm text-primary hover:underline"
              >
                Detail
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Publish control ───────────────────────────────

function PublishControl({ testId }) {
  const [open, setOpen] = useState(false)
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const [isPublished, setIsPublished] = useState(false)
  const [accessMode, setAccessMode] = useState("open")
  const [accessCode, setAccessCode] = useState("")
  const [showNames, setShowNames] = useState(true)
  const [showLeaderboard, setShowLeaderboard] = useState(false)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getPublishSettings(testId)
      setSettings(data)
      setIsPublished(data.is_published ?? false)
      setAccessMode(data.access_mode ?? "open")
      setAccessCode(data.access_code ?? "")
      setShowNames(data.show_names ?? true)
      setShowLeaderboard(data.show_leaderboard ?? false)
    } catch {
      toast.error("Failed to load publish settings")
    } finally {
      setLoading(false)
    }
  }, [testId])

  useEffect(() => {
    if (open) loadSettings()
  }, [open, loadSettings])

  async function handleSave() {
    setSaving(true)
    try {
      const body = {
        is_published: isPublished,
        access_mode: accessMode,
        show_names: showNames,
        show_leaderboard: showLeaderboard,
      }
      if (accessMode === "code" && accessCode.trim()) {
        body.access_code = accessCode.trim()
      }
      const updated = await setPublishSettings(testId, body)
      setSettings(updated)
      setIsPublished(updated.is_published ?? isPublished)
      setAccessMode(updated.access_mode ?? accessMode)
      setShowLeaderboard(updated.show_leaderboard ?? showLeaderboard)
      setShowNames(updated.show_names ?? showNames)
      toast.success("Publish settings saved")
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to save publish settings"
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  function handleCopyLink() {
    const url = settings?.public_url
    if (!url) return
    navigator.clipboard.writeText(url).then(
      () => toast.success("Link copied to clipboard"),
      () => toast.error("Failed to copy link"),
    )
  }

  return (
    <div className="mt-8 rounded-xl border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        aria-expanded={open}
      >
        <div>
          <span className="font-semibold">Share results publicly</span>
          {settings?.is_published && (
            <Badge variant="success" className="ml-2">
              Published
            </Badge>
          )}
        </div>
        <span className="text-muted-foreground" aria-hidden="true">
          {open ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </span>
      </button>

      {open && (
        <div className="border-t px-5 pb-5 pt-4">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading settings…</p>
          ) : (
            <div className="flex flex-col gap-5">
              {/* Published toggle */}
              <div className="flex items-center justify-between gap-4">
                <div>
                  <Label htmlFor="publish-toggle" className="text-sm font-medium">
                    Publish results
                  </Label>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Allow students to look up their result via a public link
                  </p>
                </div>
                <Switch
                  id="publish-toggle"
                  checked={isPublished}
                  onCheckedChange={setIsPublished}
                />
              </div>

              {/* Public link */}
              {isPublished && settings?.public_url && (
                <div className="rounded-lg border bg-muted/40 px-4 py-3">
                  <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                    Public link
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 truncate rounded bg-background px-2.5 py-1.5 text-xs font-mono">
                      {settings.public_url}
                    </code>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleCopyLink}
                    >
                      Copy
                    </Button>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Anyone with this link can look up results by roll number.
                  </p>
                </div>
              )}

              {/* Access mode */}
              <div className="flex flex-col gap-2">
                <Label className="text-sm font-medium">Access mode</Label>
                <RadioGroup
                  value={accessMode}
                  onValueChange={setAccessMode}
                  className="gap-2"
                >
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="open" id="mode-open" />
                    <Label htmlFor="mode-open" className="cursor-pointer font-normal">
                      Anyone with the link
                    </Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="code" id="mode-code" />
                    <Label htmlFor="mode-code" className="cursor-pointer font-normal">
                      Require an access code
                    </Label>
                  </div>
                </RadioGroup>
              </div>

              {/* Access code input */}
              {accessMode === "code" && (
                <div className="flex flex-col gap-1.5">
                  <Label
                    htmlFor="access-code-input"
                    className="text-sm font-medium"
                  >
                    Access code
                  </Label>
                  <Input
                    id="access-code-input"
                    type="text"
                    placeholder="Set a code students must enter"
                    value={accessCode}
                    onChange={(e) => setAccessCode(e.target.value)}
                    autoComplete="off"
                  />
                </div>
              )}

              {/* Show student names */}
              <div className="flex items-center justify-between gap-4">
                <div>
                  <Label
                    htmlFor="show-names-toggle"
                    className="text-sm font-medium"
                  >
                    Show student names
                  </Label>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Display names in results and leaderboard
                  </p>
                </div>
                <Switch
                  id="show-names-toggle"
                  checked={showNames}
                  onCheckedChange={setShowNames}
                />
              </div>

              {/* Show leaderboard */}
              <div className="flex items-center justify-between gap-4">
                <div>
                  <Label
                    htmlFor="show-leaderboard-toggle"
                    className="text-sm font-medium"
                  >
                    Show public leaderboard
                  </Label>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Display class rankings below each student's result
                  </p>
                </div>
                <Switch
                  id="show-leaderboard-toggle"
                  checked={showLeaderboard}
                  onCheckedChange={setShowLeaderboard}
                />
              </div>

              {/* Save */}
              <div className="flex justify-end pt-1">
                <Button type="button" onClick={handleSave} disabled={saving}>
                  {saving ? "Saving…" : "Save"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main Results page ─────────────────────────────

export default function Results() {
  const { testId } = useParams()
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [downloadingBulk, setDownloadingBulk] = useState(false)

  const fetchResults = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await listResults(testId)
      setResults(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load results")
    } finally {
      setLoading(false)
    }
  }, [testId])

  useEffect(() => {
    fetchResults()
  }, [fetchResults])

  async function handleBulkReportCards() {
    setDownloadingBulk(true)
    try {
      await downloadBulkReportCards(testId)
      toast.success("Report cards downloaded")
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to download report cards"
      toast.error(msg)
    } finally {
      setDownloadingBulk(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Breadcrumb
        className="mb-2"
        items={[
          { label: "Classes", to: "/classes" },
          { label: `Test #${testId}` },
          { label: "Results" },
        ]}
      />

      <PageHeader
        className="mb-4"
        title="Results"
        description={`Test #${testId}`}
        actions={
          <Button
            variant="outline"
            size="sm"
            disabled={downloadingBulk}
            onClick={handleBulkReportCards}
            className="min-h-[40px]"
          >
            {downloadingBulk ? "Downloading…" : "Download all report cards"}
          </Button>
        }
      />

      {/* Test lifecycle rail (replaces the old Scan/Review sibling buttons) */}
      <TestProgressRail testId={testId} current="results" className="mb-6" />

      {loading ? (
        <TableSkeleton rows={6} />
      ) : error ? (
        <ErrorState
          title="Couldn't load results"
          description="Something went wrong while loading results for this test."
          onRetry={fetchResults}
        />
      ) : results.length === 0 ? (
        <EmptyState
          icon={ClipboardListIcon}
          title="No results yet"
          description="Upload scanned sheets to grade students and see results here."
          action={
            <Button asChild>
              <Link to={`/tests/${testId}/scan`}>Upload scans</Link>
            </Button>
          }
        />
      ) : (
        <>
          {/* Summary row */}
          <div className="mb-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
            <span>
              {results.length} student{results.length !== 1 ? "s" : ""}
            </span>
            <span>
              Avg score:{" "}
              {results.length > 0
                ? (
                    results.reduce((s, r) => s + Number(r.score ?? 0), 0) /
                    results.length
                  ).toFixed(1)
                : "—"}
            </span>
            <span>
              Needs review: {results.filter((r) => r.needs_review).length}
            </span>
          </div>

          {/* Desktop table (md+) */}
          <div className="hidden md:block rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Roll</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Correct / Wrong / Blank</TableHead>
                  <TableHead>Flag</TableHead>
                  <TableHead className="text-right">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((r) => (
                  <StudentResultRow key={r.id} result={r} testId={testId} />
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Mobile cards (<md) */}
          <div className="flex flex-col gap-3 md:hidden">
            {results.map((r) => (
              <StudentResultCard key={r.id} result={r} testId={testId} />
            ))}
          </div>

          <p className="mt-3 text-xs text-muted-foreground">
            Click a row to expand per-question responses. Click "Detail" for
            the full analytics drill-down.
          </p>
        </>
      )}

      {/* Publish / share control — always visible */}
      <PublishControl testId={testId} />
    </div>
  )
}
