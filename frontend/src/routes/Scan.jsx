/**
 * Scan.jsx — Scan & Verify workspace (Product v2 Phase 4b)
 *
 * Route:  /tests/:testId/scan   (testId pre-filled)
 *         /scan                 (test selector shown)
 *
 * Flow:
 *  1. Upload zone (drag-drop + camera capture) → POST /omr/scan/
 *  2. Poll batch until done
 *  3. Results board: GET /omr/scan-batches/<id>/sheets/
 *     - Summary header (N sheets · M need attention · avg score)
 *     - Card per sheet (student name/roll, score, status badge)
 *     - Flagged-first ordering + All / Needs attention filter
 *  4. Inline corrector (SheetCorrectorPanel) → POST /omr/sheets/<id>/regrade/
 *
 * E2E contract (must never break):
 *  - input[type="file"] always present while upload is possible
 *  - button accessible name matches /Upload & scan/
 *  - text "processed successfully" visible once batch completes
 */
import { useEffect, useRef, useState, useCallback } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { toast } from "sonner"
import {
  CheckCircle2Icon,
  UploadIcon,
  CameraIcon,
  FlagIcon,
} from "lucide-react"
import { uploadScan, getBatch, getBatchSheets } from "@/api/scan"
import { listTests } from "@/api/assessments"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { SheetCorrectorPanel } from "@/components/SheetCorrectorPanel"

const POLL_INTERVAL_MS = 1500

// ── status badge helpers ─────────────────────────────────────────────────────

function sheetStatus(sheet) {
  // sheet.status from ScanBatchSheetsView: "done", "needs_review", "error",
  // "no_qr", "failed", "processing"
  const s = sheet.status ?? ""
  if (s === "done" && (!sheet.flags || sheet.flags.length === 0)) return "clean"
  if (s === "needs_review" || (sheet.flags && sheet.flags.length > 0)) return "attention"
  if (s === "error" || s === "no_qr" || s === "failed") return "error"
  return "clean"
}

function StatusBadge({ sheet }) {
  const st = sheetStatus(sheet)
  if (st === "clean")
    return <Badge variant="success">Clean</Badge>
  if (st === "attention")
    return <Badge variant="warning">Needs attention</Badge>
  return <Badge variant="error">Error</Badge>
}

// ── sheet card ───────────────────────────────────────────────────────────────

function SheetCard({ sheet, onOpenCorrector }) {
  const studentName = sheet.student?.name ?? "Unknown student"
  const studentRoll = sheet.student?.roll ?? sheet.detected?.roll ?? "—"
  const result = sheet.student_result
  const score = result?.score ?? null
  const maxScore = result?.max_score ?? null
  const scoreLabel =
    score != null && maxScore != null
      ? `${score} / ${maxScore}`
      : "—"

  const st = sheetStatus(sheet)

  return (
    <div
      className={`flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between ${
        st === "attention"
          ? "border-[var(--color-warning)]/40 bg-[color-mix(in_oklch,var(--color-warning)_8%,transparent)]"
          : st === "error"
          ? "border-[var(--color-error)]/40 bg-[color-mix(in_oklch,var(--color-error)_8%,transparent)]"
          : "border-border bg-card"
      }`}
    >
      <div className="flex flex-col gap-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge sheet={sheet} />
          <span className="font-medium text-sm truncate">{studentName}</span>
          <span className="text-xs text-muted-foreground">Roll: {studentRoll}</span>
        </div>
        {sheet.flags && sheet.flags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-0.5">
            {sheet.flags.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs bg-[color-mix(in_oklch,var(--color-warning)_15%,transparent)] text-[var(--color-warning)]"
              >
                <FlagIcon className="size-2.5" />
                {f}
              </span>
            ))}
          </div>
        )}
        {sheet.error_reason && (
          <span className="mt-0.5 text-xs text-[var(--color-error)]">
            {sheet.error_reason}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <div className="text-right">
          <p className="text-sm font-semibold">{scoreLabel}</p>
          <p className="text-xs text-muted-foreground">score</p>
        </div>
        <Button
          size="sm"
          variant={st === "attention" ? "default" : "outline"}
          onClick={() => onOpenCorrector(sheet)}
          className="min-h-[40px]"
        >
          {st === "attention" ? "Fix & re-grade" : "Review"}
        </Button>
      </div>
    </div>
  )
}

// ── skeleton cards ───────────────────────────────────────────────────────────

function SheetCardSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-2 flex-1">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <Skeleton className="h-8 w-12" />
        <Skeleton className="h-9 w-24" />
      </div>
    </div>
  )
}

// ── summary header ───────────────────────────────────────────────────────────

function ResultsSummary({ sheets }) {
  const total = sheets.length
  const needsAttention = sheets.filter((s) => sheetStatus(s) === "attention").length
  const errors = sheets.filter((s) => sheetStatus(s) === "error").length
  const scored = sheets.filter(
    (s) => s.student_result?.score != null && s.student_result?.max_score != null
  )
  const avgScore =
    scored.length > 0
      ? scored.reduce(
          (acc, s) => acc + s.student_result.score / s.student_result.max_score,
          0
        ) / scored.length
      : null

  return (
    <div className="flex flex-wrap gap-6 rounded-lg border border-border bg-surface-2 p-4">
      <div className="flex flex-col">
        <span className="text-2xl font-bold tabular">{total}</span>
        <span className="text-xs text-muted-foreground">sheets</span>
      </div>
      {needsAttention > 0 && (
        <div className="flex flex-col">
          <span className="text-2xl font-bold tabular text-[var(--color-warning)]">{needsAttention}</span>
          <span className="text-xs text-muted-foreground">need attention</span>
        </div>
      )}
      {errors > 0 && (
        <div className="flex flex-col">
          <span className="text-2xl font-bold tabular text-[var(--color-error)]">{errors}</span>
          <span className="text-xs text-muted-foreground">errors</span>
        </div>
      )}
      {avgScore != null && (
        <div className="flex flex-col">
          <span className="text-2xl font-bold tabular">{Math.round(avgScore * 100)}%</span>
          <span className="text-xs text-muted-foreground">avg score</span>
        </div>
      )}
    </div>
  )
}

// ── drag-drop upload zone ────────────────────────────────────────────────────

function DropZone({ onFiles, disabled, files }) {
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  const cameraInputRef = useRef(null)

  function handleDragOver(e) {
    e.preventDefault()
    if (!disabled) setDragging(true)
  }

  function handleDragLeave() {
    setDragging(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    if (disabled) return
    const dropped = Array.from(e.dataTransfer.files)
    if (dropped.length > 0) onFiles(dropped)
  }

  function handleFileChange(e) {
    const selected = Array.from(e.target.files)
    if (selected.length > 0) onFiles(selected)
    // Reset so same file can be re-selected
    e.target.value = ""
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Drag-drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 transition-colors ${
          dragging
            ? "border-primary bg-primary/5"
            : disabled
            ? "cursor-not-allowed border-border opacity-50"
            : "border-border hover:border-primary hover:bg-muted/30"
        }`}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload scanned sheets"
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault()
            fileInputRef.current?.click()
          }
        }}
      >
        <UploadIcon className="size-7 text-muted-foreground" />
        <p className="text-sm font-medium">
          {files.length > 0
            ? `${files.length} file${files.length !== 1 ? "s" : ""} selected`
            : "Drop sheet images or PDFs here"}
        </p>
        <p className="text-xs text-muted-foreground">or click to browse</p>
      </div>

      {/* Hidden desktop file input (E2E: locator 'input[type="file"]' hits this) */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,.pdf"
        className="sr-only"
        onChange={handleFileChange}
        aria-label="Select sheet files"
        tabIndex={-1}
      />

      {/* Mobile camera capture — shown separately */}
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-h-[40px] gap-1.5"
          onClick={() => cameraInputRef.current?.click()}
          disabled={disabled}
        >
          <CameraIcon className="size-4" />
          Camera (mobile)
        </Button>
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          className="sr-only"
          onChange={handleFileChange}
          aria-label="Capture with camera"
          tabIndex={-1}
        />
        {files.length > 0 && (
          <span className="text-xs text-muted-foreground ml-1">
            {files.length} file{files.length !== 1 ? "s" : ""} ready
          </span>
        )}
      </div>

      {/* File list preview */}
      {files.length > 0 && (
        <ul className="text-xs text-muted-foreground space-y-0.5 pl-1">
          {files.slice(0, 5).map((f, i) => (
            <li key={i} className="truncate">{f.name}</li>
          ))}
          {files.length > 5 && (
            <li className="text-muted-foreground">…and {files.length - 5} more</li>
          )}
        </ul>
      )}
    </div>
  )
}

// ── main component ───────────────────────────────────────────────────────────

export default function Scan() {
  const { testId: routeTestId } = useParams()
  const [searchParams] = useSearchParams()

  const [testId, setTestId] = useState(routeTestId ?? searchParams.get("test") ?? "")
  const [tests, setTests] = useState([])
  const [loadingTests, setLoadingTests] = useState(!routeTestId)

  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)

  // Batch state
  const [batch, setBatch] = useState(null)
  const [done, setDone] = useState(false)
  const pollRef = useRef(null)

  // Sheets (post-processing results board)
  const [sheets, setSheets] = useState([])
  const [loadingSheets, setLoadingSheets] = useState(false)
  const [filter, setFilter] = useState("all") // "all" | "attention"

  // Corrector panel
  const [correctorSheet, setCorrectorSheet] = useState(null)
  const [correctorOpen, setCorrectorOpen] = useState(false)

  // Load tests when not pre-selected
  useEffect(() => {
    if (routeTestId) return
    setLoadingTests(true)
    listTests()
      .then((data) => setTests(data.results ?? data))
      .catch(() => toast.error("Failed to load tests"))
      .finally(() => setLoadingTests(false))
  }, [routeTestId])

  // Cleanup poll on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // Fetch sheets after batch completes
  const fetchSheets = useCallback(async (batchId) => {
    setLoadingSheets(true)
    try {
      const data = await getBatchSheets(batchId)
      // Sort: flagged / attention first, then errors, then clean
      const sorted = [...(data ?? [])].sort((a, b) => {
        const order = { attention: 0, error: 1, clean: 2 }
        return (order[sheetStatus(a)] ?? 2) - (order[sheetStatus(b)] ?? 2)
      })
      setSheets(sorted)
    } catch {
      toast.error("Failed to load sheet results")
    } finally {
      setLoadingSheets(false)
    }
  }, [])

  const startPolling = useCallback(
    (batchId) => {
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        try {
          const data = await getBatch(batchId)
          setBatch(data)
          if (data.status === "done" || data.processed >= data.total) {
            clearInterval(pollRef.current)
            pollRef.current = null
            setDone(true)
            // Fetch per-sheet details
            fetchSheets(batchId)
          }
        } catch {
          clearInterval(pollRef.current)
          pollRef.current = null
          toast.error("Lost connection while polling scan progress")
        }
      }, POLL_INTERVAL_MS)
    },
    [fetchSheets]
  )

  async function handleUpload() {
    if (!testId) {
      toast.error("Please select a test first")
      return
    }
    if (files.length === 0) {
      toast.error("Please select at least one file")
      return
    }
    setUploading(true)
    setBatch(null)
    setDone(false)
    setSheets([])
    try {
      const resp = await uploadScan(testId, files)
      setBatch({ id: resp.batch_id, status: "processing", total: resp.total, processed: 0 })
      toast.success(`Scan started — ${resp.total} image(s) queued`)
      startPolling(resp.batch_id)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        "Upload failed"
      toast.error(msg)
    } finally {
      setUploading(false)
    }
  }

  function handleReset() {
    setBatch(null)
    setDone(false)
    setFiles([])
    setSheets([])
    setFilter("all")
  }

  function handleOpenCorrector(sheet) {
    setCorrectorSheet(sheet)
    setCorrectorOpen(true)
  }

  function handleRegraded(scanJobId, updatedResult) {
    setSheets((prev) =>
      prev.map((s) => {
        if (s.id !== scanJobId) return s
        return {
          ...s,
          status: "done",
          flags: [],
          student_result: updatedResult,
        }
      })
    )
  }

  const pct = batch
    ? Math.round(((batch.processed ?? 0) / Math.max(batch.total, 1)) * 100)
    : 0

  const filteredSheets =
    filter === "attention"
      ? sheets.filter((s) => sheetStatus(s) === "attention")
      : sheets

  const needsAttentionCount = sheets.filter((s) => sheetStatus(s) === "attention").length

  return (
    <PageShell>
      <PageHeader
        title="Scan OMR sheets"
        description={
          routeTestId
            ? "Upload scanned sheets and auto-grade. Use the lifecycle panel to move between stages."
            : "Pick a test, then upload scanned sheets to auto-grade."
        }
      />

      {/* ── Upload section ── */}
      {!done && (
        <>
          {/* Test selector */}
          {!routeTestId && (
            <div className="mb-6 flex flex-col gap-1.5">
              <Label>Test</Label>
              {loadingTests ? (
                <Skeleton className="h-8 w-full" />
              ) : tests.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No tests found.{" "}
                  <Link to="/classes" className="underline hover:text-foreground">
                    Go to classes
                  </Link>
                </p>
              ) : (
                <Select value={testId} onValueChange={setTestId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a test…" />
                  </SelectTrigger>
                  <SelectContent>
                    {tests.map((t) => (
                      <SelectItem key={t.id} value={String(t.id)}>
                        {t.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}

          {/* Drop zone */}
          <div className="mb-6">
            <Label className="mb-2 block">Scanned sheets (images or PDF)</Label>
            <DropZone
              onFiles={setFiles}
              disabled={uploading || Boolean(batch)}
              files={files}
            />
          </div>

          {/* Upload button */}
          {!batch && (
            <Button
              onClick={handleUpload}
              disabled={uploading || files.length === 0 || !testId}
              className="w-full min-h-[44px]"
            >
              {uploading ? "Uploading…" : "Upload & scan"}
            </Button>
          )}

          {/* Progress */}
          {batch && !done && (
            <div className="mt-6 flex flex-col gap-3">
              <p className="text-sm font-medium">
                Processing… {batch.processed ?? 0}/{batch.total} sheets
              </p>
              <Progress value={pct} className="h-3" />
              <p className="text-xs text-muted-foreground">{pct}% complete</p>
            </div>
          )}
        </>
      )}

      {/* ── Results board ── */}
      {done && batch && (
        <div className="flex flex-col gap-5">
          {/* Completion banner — contains "processed successfully" for E2E */}
          <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-4">
            <CheckCircle2Icon className="mt-0.5 size-5 shrink-0 text-[var(--color-success)]" />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm">
                {batch.processed} of {batch.total} sheet(s) processed successfully.
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Review results below and correct any flagged sheets.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2 shrink-0">
              <Button asChild size="sm" variant="outline">
                <Link to={`/tests/${testId}/results`}>Results</Link>
              </Button>
              <Button size="sm" variant="ghost" onClick={handleReset}>
                Scan more
              </Button>
            </div>
          </div>

          {/* Summary header */}
          {sheets.length > 0 && !loadingSheets && (
            <ResultsSummary sheets={sheets} />
          )}

          {/* Filter toggle */}
          {sheets.length > 0 && !loadingSheets && needsAttentionCount > 0 && (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setFilter("all")}
                className={`min-h-[40px] rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                  filter === "all"
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-transparent hover:bg-muted"
                }`}
              >
                All ({sheets.length})
              </button>
              <button
                type="button"
                onClick={() => setFilter("attention")}
                className={`min-h-[40px] rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                  filter === "attention"
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-transparent hover:bg-muted"
                }`}
              >
                Needs attention ({needsAttentionCount})
              </button>
            </div>
          )}

          {/* Sheet cards */}
          <div className="flex flex-col gap-3">
            {loadingSheets ? (
              <>
                <SheetCardSkeleton />
                <SheetCardSkeleton />
                <SheetCardSkeleton />
              </>
            ) : filteredSheets.length === 0 ? (
              <div className="rounded-lg border border-border p-6 text-center text-sm text-muted-foreground">
                {filter === "attention"
                  ? "No sheets need attention."
                  : "No sheets found for this batch."}
              </div>
            ) : (
              filteredSheets.map((sheet) => (
                <SheetCard
                  key={sheet.id}
                  sheet={sheet}
                  onOpenCorrector={handleOpenCorrector}
                />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Inline corrector panel ── */}
      <SheetCorrectorPanel
        sheet={correctorSheet}
        open={correctorOpen}
        onClose={() => setCorrectorOpen(false)}
        onRegraded={handleRegraded}
      />
    </PageShell>
  )
}
