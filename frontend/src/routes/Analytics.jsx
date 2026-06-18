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

function StatCard({ label, value, sub }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border bg-card p-4 shadow-sm">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-2xl font-bold tabular-nums">{value ?? "—"}</span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  )
}

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
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip />
        <Bar dataKey="count" fill="var(--color-info, #6366f1)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ToppersSection({ toppers }) {
  if (!toppers?.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No toppers data available.</p>
    )
  }
  return (
    <div className="rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">#</TableHead>
            <TableHead>Roll</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Percentage</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {toppers.map((t, i) => (
            <TableRow key={t.student?.roll ?? i}>
              <TableCell className="text-muted-foreground">{i + 1}</TableCell>
              <TableCell className="font-mono text-sm">{t.student?.roll ?? "—"}</TableCell>
              <TableCell>{t.student?.name ?? "—"}</TableCell>
              <TableCell className="tabular-nums">
                {t.score ?? "—"}/{t.max_score ?? "—"}
              </TableCell>
              <TableCell className="tabular-nums">{pct(t.score, t.max_score)}</TableCell>
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
    <div className="rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">Q#</TableHead>
            <TableHead>Question</TableHead>
            <TableHead className="w-28">Wrong rate</TableHead>
            <TableHead className="w-20">Responses</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {hardestQuestions.map((q) => (
            <TableRow key={q.question_id ?? q.order_index}>
              <TableCell className="font-mono text-sm text-muted-foreground">
                {q.order_index != null ? q.order_index + 1 : "—"}
              </TableCell>
              <TableCell className="max-w-xs truncate text-sm">{q.text ?? "—"}</TableCell>
              <TableCell>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                    parseFloat(q.wrong_rate) >= 0.7
                      ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                      : parseFloat(q.wrong_rate) >= 0.4
                      ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                      : "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                  }`}
                >
                  {fmtRate(q.wrong_rate)}
                </span>
              </TableCell>
              <TableCell className="tabular-nums text-sm text-muted-foreground">
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
          <div key={q.question_id} className="rounded-xl border p-4">
            <p className="mb-2 text-sm font-medium">{q.text ?? `Question ${q.question_id}`}</p>
            <div className="flex flex-col gap-1.5">
              {options.map((o) => {
                const barPct = total > 0 ? Math.round(((o.count ?? 0) / total) * 100) : 0
                const isCorrect = correctSet.has(String(o.label))
                return (
                  <div key={o.label} className="flex items-center gap-2 text-xs">
                    <span
                      className={`w-5 shrink-0 font-medium ${
                        isCorrect ? "text-green-600" : "text-muted-foreground"
                      }`}
                    >
                      {o.label}
                    </span>
                    <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted">
                      <div
                        className={`absolute inset-y-0 left-0 rounded transition-all ${
                          isCorrect ? "bg-green-500" : "bg-primary/40"
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
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={lineData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="attempt" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
              <Tooltip formatter={(v) => `${v}%`} />
              <Line
                type="monotone"
                dataKey="average"
                stroke="var(--color-info, #6366f1)"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {studentRows.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold">Per-student delta (latest attempt)</h3>
          <div className="rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Roll</TableHead>
                  <TableHead>Attempts</TableHead>
                  <TableHead>Latest %</TableHead>
                  <TableHead>Delta vs prev</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {studentRows.map((row) => (
                  <TableRow key={row.roll}>
                    <TableCell className="font-mono text-sm">{row.roll}</TableCell>
                    <TableCell className="tabular-nums">{row.attempts}</TableCell>
                    <TableCell className="tabular-nums">
                      {row.lastPct != null ? `${row.lastPct}%` : "—"}
                    </TableCell>
                    <TableCell>
                      {row.delta == null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : row.delta > 0 ? (
                        <span className="text-green-600">+{row.delta}%</span>
                      ) : row.delta < 0 ? (
                        <span className="text-red-500">{row.delta}%</span>
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
    too_easy: { text: "Too easy", cls: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400" },
    too_hard: { text: "Too hard", cls: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" },
    negative_discrimination: { text: "Neg. discrimination", cls: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400" },
  }
  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((f) => {
        const meta = labels[f]
        return meta ? (
          <span key={f} className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${meta.cls}`}>
            {meta.text}
          </span>
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
          <span className="font-medium text-amber-700 dark:text-amber-400">Non-functioning distractors </span>
          <span className="text-muted-foreground">(selected by &lt;5% of students):</span>
          <span className="ml-1">
            {nfdFlags.map((f) => f.replace("non_functioning_distractor:", "")).join(", ")}
          </span>
        </div>
      )}
      {miskeyFlags.length > 0 && (
        <div>
          <span className="font-medium text-red-700 dark:text-red-400">Possible miskey suspects </span>
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
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800/40 dark:bg-amber-900/20 dark:text-amber-300">
          <strong>Needs at least 10 graded students for full item analysis.</strong>
          {" "}Currently {cohortSize} student{cohortSize !== 1 ? "s" : ""} graded.
          Difficulty (p-value) is shown; discrimination, point-biserial, and KR-20 require a larger cohort.
        </div>
      )}

      {/* KR-20 reliability */}
      {kr20Display != null && (
        <div className="flex items-center gap-3 rounded-xl border bg-card p-4 shadow-sm">
          <div>
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Reliability (KR-20)
            </span>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums">{kr20Display}</span>
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
          <div className="rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">Q#</TableHead>
                  <TableHead className="w-28">Difficulty (p)</TableHead>
                  <TableHead className="w-28">Discrimination</TableHead>
                  <TableHead className="w-32">Point-biserial</TableHead>
                  <TableHead>Flags</TableHead>
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
                      ? "text-blue-600"
                      : pVal < 0.2
                      ? "text-red-500"
                      : "text-foreground"
                  return (
                    <TableRow key={item.q_pos ?? idx}>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        {(item.q_pos ?? idx) + 1}
                      </TableCell>
                      <TableCell className={`tabular-nums font-medium ${pColour}`}>
                        {pDisplay}
                      </TableCell>
                      <TableCell className="tabular-nums text-sm">
                        {smallCohort ? (
                          <span className="text-muted-foreground text-xs">—</span>
                        ) : (
                          fmtMetric(item.discrimination)
                        )}
                      </TableCell>
                      <TableCell className="tabular-nums text-sm">
                        {smallCohort ? (
                          <span className="text-muted-foreground text-xs">—</span>
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

  const fetchSummary = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getTestAnalytics(testId)
      setSummary(data)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to load analytics"
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
      <div className="mx-auto max-w-5xl px-4 py-8">
        <p className="text-sm text-muted-foreground">Loading analytics…</p>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <EmptyState
          title="No analytics data"
          description="Analytics will appear once students have been graded."
          action={
            <Button asChild variant="outline" size="sm">
              <Link to={`/tests/${testId}/results`}>View results</Link>
            </Button>
          }
        />
      </div>
    )
  }

  const test = summary.test ?? {}
  const avg = summary.average
  const median = summary.median

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Breadcrumb */}
      <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/classes" className="hover:text-foreground hover:underline">
          Classes
        </Link>
        <span>/</span>
        <span className="hover:text-foreground">
          {test.title ?? `Test #${testId}`}
        </span>
        <span>/</span>
        <span>Analytics</span>
      </div>

      <div className="mb-6 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            {test.title ?? `Test #${testId}`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/results`}>Results</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/review`}>Review queue</Link>
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="mb-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="questions">Questions</TabsTrigger>
          <TabsTrigger value="item-analysis">Item Analysis</TabsTrigger>
          <TabsTrigger value="improvement">Improvement</TabsTrigger>
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
    </div>
  )
}
