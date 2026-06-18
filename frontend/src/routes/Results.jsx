import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { listResults } from "@/api/scan"
import { getPublishSettings, setPublishSettings, downloadBulkReportCards } from "@/api/analytics"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

// Inline badge — no separate badge component needed
function NeedsReviewBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
      Needs review
    </span>
  )
}

function ScoreBadge({ score, maxScore }) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0
  const colour =
    pct >= 70
      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
      : pct >= 40
        ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colour}`}>
      {score}/{maxScore}
    </span>
  )
}

function QuestionResponseRow({ resp }) {
  return (
    <tr className="border-t border-border/40 text-xs">
      <td className="py-1 pl-8 pr-2 text-muted-foreground">Q{resp.q_pos ?? resp.question}</td>
      <td className="px-2 py-1">
        {resp.marked_options?.length > 0 ? resp.marked_options.join(", ") : <span className="italic text-muted-foreground">blank</span>}
      </td>
      <td className="px-2 py-1">
        {resp.flagged ? (
          <span className="text-yellow-600">⚠ flagged</span>
        ) : resp.is_correct ? (
          <span className="text-green-600">✓</span>
        ) : (
          <span className="text-red-500">✗</span>
        )}
      </td>
    </tr>
  )
}

function StudentResultRow({ result, testId }) {
  const [expanded, setExpanded] = useState(false)
  const responses = result.responses ?? result.question_responses ?? []
  // The API returns `student` as the FK id plus flat `student_roll`/`student_name`.
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
          <span className="text-green-600">{result.correct_count ?? 0}✓</span>
          {" / "}
          <span className="text-red-500">{result.wrong_count ?? 0}✗</span>
          {" / "}
          <span>{result.blank_count ?? 0}—</span>
        </TableCell>
        <TableCell>
          {result.needs_review ? <NeedsReviewBadge /> : null}
        </TableCell>
        <TableCell className="text-right text-xs text-muted-foreground" onClick={(e) => e.stopPropagation()}>
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
            <span>{expanded ? "▲ collapse" : "▼ expand"}</span>
          </div>
        </TableCell>
      </TableRow>

      {expanded && responses.length > 0 && (
        <TableRow className="bg-muted/20">
          <TableCell colSpan={6} className="p-0">
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
          </TableCell>
        </TableRow>
      )}

      {expanded && responses.length === 0 && (
        <TableRow className="bg-muted/20">
          <TableCell colSpan={6} className="py-2 pl-8 text-xs text-muted-foreground">
            No per-question responses recorded.
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

// ────────────────────────────────────────────────
// Publish control
// ────────────────────────────────────────────────

function PublishControl({ testId }) {
  const [open, setOpen] = useState(false)
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Form state
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
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
        aria-expanded={open}
      >
        <div>
          <span className="font-semibold">Share results publicly</span>
          {settings?.is_published && (
            <span className="ml-2 inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
              Published
            </span>
          )}
        </div>
        <span className="text-muted-foreground" aria-hidden="true">
          {open ? "▲" : "▼"}
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

              {/* Public link (when published) */}
              {isPublished && settings?.public_url && (
                <div className="rounded-lg border bg-muted/40 px-4 py-3">
                  <p className="mb-1.5 text-xs font-medium text-muted-foreground">Public link</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 truncate rounded bg-background px-2.5 py-1.5 text-xs font-mono">
                      {settings.public_url}
                    </code>
                    <Button type="button" variant="outline" size="sm" onClick={handleCopyLink}>
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
                <RadioGroup value={accessMode} onValueChange={setAccessMode} className="gap-2">
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

              {/* Access code input (conditional) */}
              {accessMode === "code" && (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="access-code-input" className="text-sm font-medium">
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
                  <Label htmlFor="show-names-toggle" className="text-sm font-medium">
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
                  <Label htmlFor="show-leaderboard-toggle" className="text-sm font-medium">
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

// ────────────────────────────────────────────────
// Main Results page
// ────────────────────────────────────────────────

export default function Results() {
  const { testId } = useParams()
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [downloadingBulk, setDownloadingBulk] = useState(false)

  const fetchResults = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listResults(testId)
      setResults(data.results ?? data)
    } catch {
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
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Results</h1>
          <p className="text-sm text-muted-foreground">Test #{testId}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={downloadingBulk}
            onClick={handleBulkReportCards}
          >
            {downloadingBulk ? "Downloading…" : "Download all report cards"}
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/scan`}>Scan more</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/review`}>Review queue</Link>
          </Button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading results…</p>
      ) : results.length === 0 ? (
        <div className="rounded-xl border p-8 text-center">
          <p className="mb-3 text-muted-foreground">No results yet for this test.</p>
          <Button asChild size="sm">
            <Link to={`/tests/${testId}/scan`}>Upload scans</Link>
          </Button>
        </div>
      ) : (
        <>
          {/* Summary row */}
          <div className="mb-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
            <span>{results.length} student{results.length !== 1 ? "s" : ""}</span>
            <span>
              Avg score:{" "}
              {results.length > 0
                ? (
                    results.reduce((s, r) => s + Number(r.score ?? 0), 0) / results.length
                  ).toFixed(1)
                : "—"}
            </span>
            <span>
              Needs review:{" "}
              {results.filter((r) => r.needs_review).length}
            </span>
          </div>

          <div className="rounded-xl border">
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

          <p className="mt-3 text-xs text-muted-foreground">
            Click a row to expand per-question responses. Click "Detail" for the full analytics drill-down.
          </p>
        </>
      )}

      {/* Publish / share control — always visible */}
      <PublishControl testId={testId} />
    </div>
  )
}
