import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts"
import { getTestAnalytics, getImprovement, exportResults, getTestProfile } from "@/api/analytics"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatCard } from "@/components/ui/stat-card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { Skeleton } from "@/components/ui/skeleton"
import { CardGridSkeleton } from "@/components/ui/skeletons"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { BarChart2 } from "lucide-react"

const HEAD_CLASS = "sticky top-0 z-10 h-9 bg-surface-1 px-3 text-xs font-medium text-muted-foreground"

// ────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────

function pct(score, max) {
  if (!max) return "—"
  return `${Math.round((score / max) * 100)}%`
}

function fmtRate(rate) {
  if (rate == null) return "—"
  const n = typeof rate === "number" ? rate : parseFloat(rate)
  return `${Math.round(n * 100)}%`
}

// ────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────


function DistributionChart({ distribution }) {
  if (!distribution?.length) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No distribution data available.
      </p>
    )
  }
  const data = distribution.map((d) => ({ bucket: d.bucket, count: d.count }))
  return (
    // min-w-0 lets ResponsiveContainer shrink to 320px without clipping
    <div className="w-full min-w-0">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 16, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="bucket"
            tick={{ fontSize: 10 }}
            interval={0}
            angle={-30}
            textAnchor="end"
            height={44}
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 10 }} width={28} />
          <Tooltip />
          <Bar dataKey="count" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ToppersSection({ toppers }) {
  if (!toppers?.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No toppers data available.</p>
    )
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={`${HEAD_CLASS} w-8`}>#</TableHead>
            <TableHead className={HEAD_CLASS}>Roll</TableHead>
            <TableHead className={HEAD_CLASS}>Name</TableHead>
            <TableHead className={HEAD_CLASS}>Score</TableHead>
            <TableHead className={HEAD_CLASS}>Percentage</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {toppers.map((t, i) => (
            <TableRow key={t.student?.roll ?? i}>
              <TableCell className="tabular text-muted-foreground">{i + 1}</TableCell>
              <TableCell className="font-mono text-xs tabular">{t.student?.roll ?? "—"}</TableCell>
              <TableCell>{t.student?.name ?? "—"}</TableCell>
              <TableCell className="tabular">
                {t.score ?? "—"}/{t.max_score ?? "—"}
              </TableCell>
              <TableCell className="tabular">{pct(t.score, t.max_score)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function HardestQuestionsSection({ hardestQuestions }) {
  if (!hardestQuestions?.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No question difficulty data available.</p>
    )
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={`${HEAD_CLASS} w-12`}>Q#</TableHead>
            <TableHead className={HEAD_CLASS}>Question</TableHead>
            <TableHead className={`${HEAD_CLASS} w-28`}>Wrong rate</TableHead>
            <TableHead className={`${HEAD_CLASS} w-20`}>Responses</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {hardestQuestions.map((q) => (
            <TableRow key={q.question_id ?? q.order_index}>
              <TableCell className="font-mono text-xs tabular text-muted-foreground">
                {q.order_index != null ? q.order_index + 1 : "—"}
              </TableCell>
              <TableCell className="max-w-xs truncate text-sm">{q.text ?? "—"}</TableCell>
              <TableCell>
                <Badge
                  variant={
                    parseFloat(q.wrong_rate) >= 0.7
                      ? "error"
                      : parseFloat(q.wrong_rate) >= 0.4
                      ? "warning"
                      : "success"
                  }
                >
                  {fmtRate(q.wrong_rate)}
                </Badge>
              </TableCell>
              <TableCell className="tabular text-sm text-muted-foreground">
                {q.n ?? "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function OptionDistributionSection({ optionDistribution }) {
  if (!optionDistribution?.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No option distribution data available.</p>
    )
  }
  return (
    <div className="flex flex-col gap-4">
      {optionDistribution.map((q) => {
        const correctSet = new Set((q.correct ?? []).map(String))
        const options = q.options ?? []
        const total = options.reduce((s, o) => s + (o.count ?? 0), 0)
        return (
          <div key={q.question_id} className="rounded-lg border border-border p-4">
            <p className="mb-2 text-sm font-medium">{q.text ?? `Question ${q.question_id}`}</p>
            <div className="flex flex-col gap-1.5">
              {options.map((o) => {
                const barPct = total > 0 ? Math.round(((o.count ?? 0) / total) * 100) : 0
                const isCorrect = correctSet.has(String(o.label))
                return (
                  <div key={o.label} className="flex items-center gap-2 text-xs">
                    <span
                      className={`w-5 shrink-0 font-medium ${
                        isCorrect ? "text-[var(--color-success)]" : "text-muted-foreground"
                      }`}
                    >
                      {o.label}
                    </span>
                    <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted">
                      <div
                        className={`absolute inset-y-0 left-0 rounded transition-all ${
                          isCorrect ? "bg-[var(--color-success)]" : "bg-primary/40"
                        }`}
                        style={{ width: `${barPct}%` }}
                      />
                    </div>
                    <span className="w-10 shrink-0 text-right text-muted-foreground">
                      {barPct}%
                    </span>
                    <span className="w-8 shrink-0 text-right text-muted-foreground">
                      ({o.count ?? 0})
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ────────────────────────────────────────────────
// Improvement tab
// ────────────────────────────────────────────────

function ImprovementTab({ testId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getImprovement(testId)
      .then(setData)
      .catch((err) => {
        const msg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          "Failed to load improvement data"
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [testId])

  if (loading) {
    return <p className="py-8 text-sm text-muted-foreground">Loading improvement data…</p>
  }

  if (error) {
    return (
      <EmptyState
        title="No improvement data"
        description={error}
      />
    )
  }

  // Defensive: check for chain / attempts
  const chain = data?.chain ?? []
  const classAverage = data?.class_average ?? {}
  const students = data?.students ?? {}

  const hasChain = chain.length > 0 || Object.keys(classAverage).length > 0

  if (!hasChain) {
    return (
      <EmptyState
        title="No retest chain"
        description="This test hasn't been retested yet. Create a retest to track improvement over attempts."
      />
    )
  }

  // Build line chart data from class_average: { attempt: pct }
  const lineData = Object.entries(classAverage)
    .map(([attempt, avgPct]) => ({
      attempt: `Attempt ${attempt}`,
      average: typeof avgPct === "number" ? Math.round(avgPct * 100) / 100 : avgPct,
    }))
    .sort((a, b) => {
      const na = parseInt(a.attempt.replace("Attempt ", ""), 10)
      const nb = parseInt(b.attempt.replace("Attempt ", ""), 10)
      return na - nb
    })

  // Build per-student delta table
  const studentRows = []
  for (const [roll, attempts] of Object.entries(students)) {
    if (!Array.isArray(attempts) || attempts.length === 0) continue
    const last = attempts[attempts.length - 1]
    const delta = last.delta_vs_prev ?? null
    studentRows.push({
      roll,
      attempts: attempts.length,
      lastPct: last.pct ?? null,
      delta,
    })
  }

  return (
    <div className="flex flex-col gap-8">
      {lineData.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold">Class average by attempt</h3>
          <div className="w-full min-w-0">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={lineData} margin={{ top: 4, right: 8, bottom: 4, left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="attempt" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" width={36} />
                <Tooltip formatter={(v) => `${v}%`} />
                <Line
                  type="monotone"
                  dataKey="average"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {studentRows.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold">Per-student delta (latest attempt)</h3>
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className={HEAD_CLASS}>Roll</TableHead>
                  <TableHead className={HEAD_CLASS}>Attempts</TableHead>
                  <TableHead className={HEAD_CLASS}>Latest %</TableHead>
                  <TableHead className={HEAD_CLASS}>Delta vs prev</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {studentRows.map((row) => (
                  <TableRow key={row.roll}>
                    <TableCell className="font-mono text-xs tabular">{row.roll}</TableCell>
                    <TableCell className="tabular">{row.attempts}</TableCell>
                    <TableCell className="tabular">
                      {row.lastPct != null ? `${row.lastPct}%` : "—"}
                    </TableCell>
                    <TableCell className="tabular">
                      {row.delta == null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : row.delta > 0 ? (
                        <span className="text-[var(--color-success)]">+{row.delta}%</span>
                      ) : row.delta < 0 ? (
                        <span className="text-[var(--color-error)]">{row.delta}%</span>
                      ) : (
                        <span className="text-muted-foreground">0%</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────
// Item Analysis tab
// ────────────────────────────────────────────────

function ItemFlag({ flags }) {
  if (!flags?.length) return null
  const labels = {
    too_easy: { text: "Too easy", variant: "info" },
    too_hard: { text: "Too hard", variant: "error" },
    negative_discrimination: { text: "Neg. discrimination", variant: "warning" },
  }
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((f) => {
        const meta = labels[f]
        return meta ? (
          <Badge key={f} variant={meta.variant}>{meta.text}</Badge>
        ) : null
      })}
    </div>
  )
}

function fmtMetric(val) {
  if (val == null) return "—"
  if (typeof val === "object" && val.status === "insufficient_sample") return "—"
  if (typeof val === "number") return val.toFixed(3)
  return "—"
}

function DistractorSummary({ items }) {
  // Only show if at least one item has distractor data
  const itemsWithDistractor = items.filter(
    (it) => it.distractor && Array.isArray(it.distractor.options) && it.distractor.options.length > 0,
  )
  if (!itemsWithDistractor.length) return null

  const allFlags = itemsWithDistractor.flatMap((it) => it.distractor.flags ?? [])
  const nfdFlags = allFlags.filter((f) => f.startsWith("non_functioning_distractor:"))
  const miskeyFlags = allFlags.filter((f) => f.startsWith("miskey_suspect:"))

  if (!allFlags.length) {
    return (
      <p className="text-sm text-muted-foreground">No distractor flags detected.</p>
    )
  }

  return (
    <div className="flex flex-col gap-2 text-sm">
      {nfdFlags.length > 0 && (
        <div>
          <span className="font-medium text-[var(--color-warning)]">Non-functioning distractors </span>
          <span className="text-muted-foreground">(selected by &lt;5% of students):</span>
          <span className="ml-1">
            {nfdFlags.map((f) => f.replace("non_functioning_distractor:", "")).join(", ")}
          </span>
        </div>
      )}
      {miskeyFlags.length > 0 && (
        <div>
          <span className="font-medium text-[var(--color-error)]">Possible miskey suspects </span>
          <span className="text-muted-foreground">(high scorers chose distractor more than key):</span>
          <span className="ml-1">
            {miskeyFlags.map((f) => f.replace("miskey_suspect:", "")).join(", ")}
          </span>
        </div>
      )}
    </div>
  )
}

function ItemAnalysisTab({ testId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getTestProfile(testId)
      .then(setData)
      .catch((err) => {
        const msg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          "Failed to load item analysis"
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [testId])

  if (loading) {
    return <p className="py-8 text-sm text-muted-foreground">Loading item analysis…</p>
  }

  if (error) {
    return <EmptyState title="Item analysis unavailable" description={error} />
  }

  const profile = data?.profile ?? {}
  const cohortSize = data?.cohort_size ?? 0
  const items = profile.items ?? []
  const kr20Value = profile.kr20

  // Small-cohort: show note but still render what we can
  const smallCohort = cohortSize < 10

  // KR-20 display
  const kr20Display = (() => {
    if (kr20Value == null) return null
    if (typeof kr20Value === "object" && kr20Value.status === "insufficient_sample") return null
    if (typeof kr20Value === "number") return kr20Value.toFixed(3)
    return null
  })()

  const kr20Label = (() => {
    if (kr20Display == null) return null
    const v = parseFloat(kr20Display)
    if (v >= 0.8) return "Good reliability"
    if (v >= 0.6) return "Acceptable reliability"
    if (v >= 0.4) return "Questionable reliability"
    return "Poor reliability"
  })()

  if (!items.length && !smallCohort) {
    return (
      <EmptyState
        title="No item data"
        description="Item analysis will appear once the test has been graded."
      />
    )
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Small-cohort notice */}
      {smallCohort && (
        <div className="rounded-lg border border-[var(--color-warning)]/40 bg-[color-mix(in_oklch,var(--color-warning)_10%,transparent)] px-4 py-3 text-sm text-[var(--color-warning)]">
          <strong>Needs at least 10 graded students for full item analysis.</strong>
          {" "}Currently {cohortSize} student{cohortSize !== 1 ? "s" : ""} graded.
          Difficulty (p-value) is shown; discrimination, point-biserial, and KR-20 require a larger cohort.
        </div>
      )}

      {/* KR-20 reliability */}
      {kr20Display != null && (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
          <div>
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Reliability (KR-20)
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular">{kr20Display}</span>
              <span className="text-sm text-muted-foreground">{kr20Label}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              KR-20 measures internal consistency (0 = none, 1 = perfect). 0.7+ is acceptable for classroom assessments.
            </p>
          </div>
        </div>
      )}

      {/* Per-item table */}
      {items.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold">Per-item psychometrics</h3>
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className={`${HEAD_CLASS} w-12`}>Q#</TableHead>
                  <TableHead className={`${HEAD_CLASS} w-28`}>Difficulty (p)</TableHead>
                  <TableHead className={`${HEAD_CLASS} w-28`}>Discrimination</TableHead>
                  <TableHead className={`${HEAD_CLASS} w-32`}>Point-biserial</TableHead>
                  <TableHead className={HEAD_CLASS}>Flags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item, idx) => {
                  const pVal = typeof item.difficulty === "number" ? item.difficulty : null
                  const pDisplay = pVal != null ? pVal.toFixed(3) : "—"
                  const pColour =
                    pVal == null
                      ? ""
                      : pVal > 0.9
                      ? "text-[var(--color-info)]"
                      : pVal < 0.2
                      ? "text-[var(--color-error)]"
                      : "text-foreground"
                  return (
                    <TableRow key={item.q_pos ?? idx}>
                      <TableCell className="font-mono text-xs tabular text-muted-foreground">
                        {(item.q_pos ?? idx) + 1}
                      </TableCell>
                      <TableCell className={`tabular font-medium ${pColour}`}>
                        {pDisplay}
                      </TableCell>
                      <TableCell className="tabular text-sm">
                        {smallCohort ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : (
                          fmtMetric(item.discrimination)
                        )}
                      </TableCell>
                      <TableCell className="tabular text-sm">
                        {smallCohort ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : (
                          fmtMetric(item.point_biserial)
                        )}
                      </TableCell>
                      <TableCell>
                        <ItemFlag flags={item.flags} />
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            p-value: proportion correct (higher = easier). Discrimination: top 27% − bottom 27% correct rate. Point-biserial: item–total correlation.
          </p>
        </div>
      )}

      {/* Distractor summary */}
      {items.length > 0 && !smallCohort && (
        <div>
          <h3 className="mb-3 text-sm font-semibold">Distractor summary</h3>
          <DistractorSummary items={items} />
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────
// Export buttons
// ────────────────────────────────────────────────

function ExportButtons({ testId }) {
  const [exporting, setExporting] = useState(null)

  async function handleExport(fmt) {
    setExporting(fmt)
    try {
      await exportResults(testId, fmt)
      toast.success(`Exported as ${fmt.toUpperCase()}`)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        `Export failed`
      toast.error(msg)
    } finally {
      setExporting(null)
    }
  }

  const formats = [
    { key: "csv", label: "Export CSV" },
    { key: "xlsx", label: "Export Excel" },
    { key: "pdf", label: "Export PDF" },
  ]

  return (
    <div className="flex flex-wrap gap-2">
      {formats.map(({ key, label }) => (
        <Button
          key={key}
          variant="outline"
          size="sm"
          disabled={exporting != null}
          onClick={() => handleExport(key)}
        >
          {exporting === key ? "Downloading…" : label}
        </Button>
      ))}
    </div>
  )
}

// ────────────────────────────────────────────────
// Main Analytics page
// ────────────────────────────────────────────────

export default function Analytics() {
  const { testId } = useParams()
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchSummary = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getTestAnalytics(testId)
      setSummary(data)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to load analytics"
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [testId])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  if (loading) {
    return (
      <PageShell>
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-56" />
        </div>
        <CardGridSkeleton count={5} className="lg:grid-cols-5" />
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Couldn't load analytics"
          description={error}
          onRetry={fetchSummary}
        />
      </PageShell>
    )
  }

  if (!summary) {
    return (
      <PageShell>
        <EmptyState
          icon={BarChart2}
          title="No analytics data"
          description="Analytics will appear once students have been graded."
          action={
            <Button asChild variant="outline" size="sm">
              <Link to={`/tests/${testId}/results`}>View results</Link>
            </Button>
          }
        />
      </PageShell>
    )
  }

  const test = summary.test ?? {}
  const avg = summary.average
  const median = summary.median

  return (
    <PageShell>
      <PageHeader
        title="Analytics"
        description={test.title ?? `Test #${testId}`}
      />

      <Tabs defaultValue="overview">
        {/* Underline skin; horizontally scrollable on mobile so all tabs
            (incl. Item Analysis) stay reachable without wrapping/clipping. */}
        <TabsList
          variant="line"
          className="mb-6 max-w-full overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          <TabsTrigger value="overview" className="flex-none shrink-0">Overview</TabsTrigger>
          <TabsTrigger value="questions" className="flex-none shrink-0">Questions</TabsTrigger>
          <TabsTrigger value="item-analysis" className="flex-none shrink-0">Item Analysis</TabsTrigger>
          <TabsTrigger value="improvement" className="flex-none shrink-0">Improvement</TabsTrigger>
        </TabsList>

        {/* ── Overview tab ── */}
        <TabsContent value="overview">
          <div className="flex flex-col gap-8">
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              <StatCard label="Students" value={summary.n_students} />
              <StatCard label="Graded" value={summary.graded} />
              <StatCard
                label="Average"
                value={avg != null ? `${Math.round(avg * 10) / 10}` : "—"}
                sub={summary.max_score ? `/ ${summary.max_score}` : undefined}
              />
              <StatCard
                label="Median"
                value={median != null ? `${Math.round(median * 10) / 10}` : "—"}
              />
              <StatCard
                label="Needs review"
                value={summary.needs_review_count ?? 0}
              />
            </div>

            {/* Score range */}
            {(summary.max != null || summary.min != null) && (
              <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                <span>
                  High: <strong className="text-foreground">{summary.max ?? "—"}</strong>
                </span>
                <span>
                  Low: <strong className="text-foreground">{summary.min ?? "—"}</strong>
                </span>
              </div>
            )}

            {/* Distribution chart */}
            <div>
              <h2 className="mb-3 text-sm font-semibold">Score distribution</h2>
              <DistributionChart distribution={summary.distribution} />
            </div>

            {/* Toppers */}
            <div>
              <h2 className="mb-3 text-sm font-semibold">Top performers</h2>
              <ToppersSection toppers={summary.toppers} />
            </div>

            {/* Export */}
            <div>
              <h2 className="mb-3 text-sm font-semibold">Export results</h2>
              <ExportButtons testId={testId} />
            </div>
          </div>
        </TabsContent>

        {/* ── Questions tab ── */}
        <TabsContent value="questions">
          <div className="flex flex-col gap-8">
            {/* Hardest questions */}
            <div>
              <h2 className="mb-3 text-sm font-semibold">Hardest questions</h2>
              <HardestQuestionsSection hardestQuestions={summary.hardest_questions} />
            </div>

            {/* Option distribution */}
            <div>
              <h2 className="mb-3 text-sm font-semibold">Option distribution</h2>
              <OptionDistributionSection optionDistribution={summary.option_distribution} />
            </div>
          </div>
        </TabsContent>

        {/* ── Item Analysis tab ── */}
        <TabsContent value="item-analysis">
          <ItemAnalysisTab testId={testId} />
        </TabsContent>

        {/* ── Improvement tab ── */}
        <TabsContent value="improvement">
          <ImprovementTab testId={testId} />
        </TabsContent>
      </Tabs>
    </PageShell>
  )
}
