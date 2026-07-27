import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { getStudentDetail, downloadStudentReportCard } from "@/api/analytics"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/skeletons"
import { Skeleton } from "@/components/ui/skeleton"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Card, CardContent } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const HEAD_CLASS = "sticky top-0 z-10 h-9 bg-surface-1 px-3 text-xs font-medium text-muted-foreground"

function TopicAccuracySection({ topicAccuracy }) {
  const entries = Object.entries(topicAccuracy ?? {})
  if (!entries.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No topic data available.</p>
    )
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={HEAD_CLASS}>Topic</TableHead>
            <TableHead className={`${HEAD_CLASS} w-24 text-right`}>Correct</TableHead>
            <TableHead className={`${HEAD_CLASS} w-24 text-right`}>Total</TableHead>
            <TableHead className={`${HEAD_CLASS} w-28 text-right`}>Accuracy</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([topic, stat]) => {
            const pct = stat.accuracy != null ? Math.round(stat.accuracy * 100) : 0
            const colour =
              pct >= 70
                ? "text-[var(--color-success)]"
                : pct >= 40
                ? "text-[var(--color-warning)]"
                : "text-[var(--color-error)]"
            return (
              <TableRow key={topic}>
                <TableCell className="font-medium">{topic}</TableCell>
                <TableCell className="text-right tabular">{stat.correct ?? 0}</TableCell>
                <TableCell className="text-right tabular">{stat.total ?? 0}</TableCell>
                <TableCell className={`text-right tabular font-medium ${colour}`}>
                  {pct}%
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

function PerQuestionSection({ perQuestion }) {
  if (!perQuestion?.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No per-question data available.</p>
    )
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className={`${HEAD_CLASS} w-12`}>Q#</TableHead>
            <TableHead className={HEAD_CLASS}>Question</TableHead>
            <TableHead className={`${HEAD_CLASS} w-28`}>Marked</TableHead>
            <TableHead className={`${HEAD_CLASS} w-24 text-center`}>Result</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {perQuestion.map((q, i) => (
            <TableRow key={q.order_index ?? i}>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {q.order_index != null ? q.order_index + 1 : i + 1}
              </TableCell>
              <TableCell className="max-w-xs truncate text-sm">
                {q.text || <span className="italic text-muted-foreground">n/a</span>}
              </TableCell>
              <TableCell className="text-sm">
                {q.marked_options?.length > 0 ? (
                  q.marked_options.join(", ")
                ) : (
                  <span className="italic text-muted-foreground">blank</span>
                )}
              </TableCell>
              <TableCell className="text-center">
                {q.flagged ? (
                  <span className="text-xs text-[var(--color-warning)]">flagged</span>
                ) : q.is_correct ? (
                  <span className="font-medium text-[var(--color-success)]">✓</span>
                ) : (
                  <span className="font-medium text-[var(--color-error)]">✗</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export default function StudentDetail() {
  const { testId, studentId } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const fetchDetail = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const result = await getStudentDetail(testId, studentId)
      setData(result)
    } catch {
      setError(true)
      toast.error("Failed to load student detail")
    } finally {
      setLoading(false)
    }
  }, [testId, studentId])

  useEffect(() => {
    fetchDetail()
  }, [fetchDetail])

  async function handleDownloadReportCard() {
    setDownloading(true)
    try {
      await downloadStudentReportCard(testId, studentId)
      toast.success("Report card downloaded")
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to download report card"
      toast.error(msg)
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <PageShell>
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-32 w-full rounded-lg" />
        <TableSkeleton rows={4} />
        <TableSkeleton rows={5} />
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Couldn't load student detail"
          description="Something went wrong while loading this student's results."
          onRetry={fetchDetail}
        />
        <div className="text-center">
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/results`}>Back to results</Link>
          </Button>
        </div>
      </PageShell>
    )
  }

  if (!data) {
    return (
      <PageShell>
        <EmptyState
          title="No data found"
          description="We couldn't find results for this student."
          action={
            <Button asChild variant="outline" size="sm">
              <Link to={`/tests/${testId}/results`}>Back to results</Link>
            </Button>
          }
        />
      </PageShell>
    )
  }

  const score = data.score ?? 0
  const maxScore = data.max_score ?? 0
  const pct = data.pct != null ? Math.round(data.pct) : (maxScore > 0 ? Math.round((score / maxScore) * 100) : 0)
  const pctColour =
    pct >= 70
      ? "text-[var(--color-success)]"
      : pct >= 40
      ? "text-[var(--color-warning)]"
      : "text-[var(--color-error)]"

  return (
    <PageShell>
      <PageHeader
        title="Student Detail"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              className="min-h-[40px]"
              disabled={downloading}
              onClick={handleDownloadReportCard}
            >
              {downloading ? "Downloading…" : "Download report card"}
            </Button>
            <Button asChild variant="outline" size="sm" className="min-h-[40px]">
              <Link to={`/tests/${testId}/results`}>Back to results</Link>
            </Button>
          </div>
        }
      />

      {/* Score summary */}
      <Card>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Score
              </span>
              <span className="text-2xl font-bold tabular">
                {score}/{maxScore}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Percentage
              </span>
              <span className={`text-2xl font-bold tabular ${pctColour}`}>{pct}%</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Correct / Wrong / Blank
              </span>
              <span className="text-sm font-medium">
                <span className="text-[var(--color-success)]">{data.correct ?? 0}✓</span>
                {" / "}
                <span className="text-[var(--color-error)]">{data.wrong ?? 0}✗</span>
                {" / "}
                <span>{data.blank ?? 0}</span>
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Rank / Percentile
              </span>
              <span className="text-lg font-bold tabular">
                {data.rank != null ? `#${data.rank}` : "n/a"}
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {data.percentile != null
                    ? `${Math.round(data.percentile)}th pct.`
                    : "n/a"}
                </span>
              </span>
              {data.cohort_size != null && (
                <span className="text-xs text-muted-foreground">
                  of {data.cohort_size} students
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Topic accuracy */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Topic accuracy</h2>
        <TopicAccuracySection topicAccuracy={data.topic_accuracy} />
      </section>

      {/* Per-question breakdown */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Per-question breakdown</h2>
        <PerQuestionSection perQuestion={data.per_question} />
      </section>
    </PageShell>
  )
}
