import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { getStudentDetail, downloadStudentReportCard } from "@/api/analytics"
import { Button } from "@/components/ui/button"
import { Breadcrumb } from "@/components/ui/breadcrumb"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { DetailHeaderSkeleton, TableSkeleton } from "@/components/ui/list-skeletons"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function TopicAccuracySection({ topicAccuracy }) {
  const entries = Object.entries(topicAccuracy ?? {})
  if (!entries.length) {
    return (
      <p className="py-4 text-sm text-muted-foreground">No topic data available.</p>
    )
  }
  return (
    <div className="overflow-x-auto rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Topic</TableHead>
            <TableHead className="w-24 text-right">Correct</TableHead>
            <TableHead className="w-24 text-right">Total</TableHead>
            <TableHead className="w-28 text-right">Accuracy</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([topic, stat]) => {
            const pct = stat.accuracy != null ? Math.round(stat.accuracy * 100) : 0
            const colour =
              pct >= 70
                ? "text-green-600"
                : pct >= 40
                ? "text-amber-600 dark:text-amber-400"
                : "text-red-500"
            return (
              <TableRow key={topic}>
                <TableCell className="font-medium">{topic}</TableCell>
                <TableCell className="text-right tabular-nums">{stat.correct ?? 0}</TableCell>
                <TableCell className="text-right tabular-nums">{stat.total ?? 0}</TableCell>
                <TableCell className={`text-right tabular-nums font-medium ${colour}`}>
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
    <div className="overflow-x-auto rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">Q#</TableHead>
            <TableHead>Question</TableHead>
            <TableHead className="w-28">Marked</TableHead>
            <TableHead className="w-24 text-center">Result</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {perQuestion.map((q, i) => (
            <TableRow key={q.order_index ?? i}>
              <TableCell className="font-mono text-sm text-muted-foreground">
                {q.order_index != null ? q.order_index + 1 : i + 1}
              </TableCell>
              <TableCell className="max-w-xs truncate text-sm">
                {q.text || <span className="italic text-muted-foreground">—</span>}
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
                  <span className="text-yellow-600 text-xs">flagged</span>
                ) : q.is_correct ? (
                  <span className="text-green-600 font-medium">✓</span>
                ) : (
                  <span className="text-red-500 font-medium">✗</span>
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
      <div className="mx-auto max-w-4xl px-4 py-8">
        <DetailHeaderSkeleton className="mb-8" />
        <Skeleton className="mb-8 h-32 w-full rounded-2xl" />
        <Skeleton className="mb-3 h-5 w-40" />
        <TableSkeleton rows={4} className="mb-8" />
        <Skeleton className="mb-3 h-5 w-48" />
        <TableSkeleton rows={5} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <ErrorState
          title="Couldn't load student detail"
          description="Something went wrong while loading this student's results."
          onRetry={fetchDetail}
        />
        <div className="mt-4 text-center">
          <Button asChild variant="outline" size="sm">
            <Link to={`/tests/${testId}/results`}>Back to results</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <EmptyState
          title="No data found"
          description="We couldn't find results for this student."
          action={
            <Button asChild variant="outline" size="sm">
              <Link to={`/tests/${testId}/results`}>Back to results</Link>
            </Button>
          }
        />
      </div>
    )
  }

  const score = data.score ?? 0
  const maxScore = data.max_score ?? 0
  const pct = data.pct != null ? Math.round(data.pct) : (maxScore > 0 ? Math.round((score / maxScore) * 100) : 0)
  const pctColour =
    pct >= 70
      ? "text-green-600"
      : pct >= 40
      ? "text-amber-600 dark:text-amber-400"
      : "text-red-500"

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Breadcrumb */}
      <Breadcrumb
        className="mb-4"
        items={[
          { label: "Classes", to: "/classes" },
          { label: `Test #${testId}` },
          { label: "Results", to: `/tests/${testId}/results` },
          { label: `Student #${studentId}` },
        ]}
      />

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold">Student Detail</h1>
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
      </div>

      {/* Score summary */}
      <div className="mb-8 rounded-2xl border bg-background p-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Score
            </span>
            <span className="text-2xl font-bold tabular-nums">
              {score}/{maxScore}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Percentage
            </span>
            <span className={`text-2xl font-bold tabular-nums ${pctColour}`}>{pct}%</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Correct / Wrong / Blank
            </span>
            <span className="text-sm font-medium">
              <span className="text-green-600">{data.correct ?? 0}✓</span>
              {" / "}
              <span className="text-red-500">{data.wrong ?? 0}✗</span>
              {" / "}
              <span>{data.blank ?? 0}—</span>
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Rank / Percentile
            </span>
            <span className="text-lg font-bold tabular-nums">
              {data.rank != null ? `#${data.rank}` : "—"}
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {data.percentile != null
                  ? `${Math.round(data.percentile)}th pct.`
                  : "—"}
              </span>
            </span>
            {data.cohort_size != null && (
              <span className="text-xs text-muted-foreground">
                of {data.cohort_size} students
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Topic accuracy */}
      <div className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Topic accuracy</h2>
        <TopicAccuracySection topicAccuracy={data.topic_accuracy} />
      </div>

      {/* Per-question breakdown */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Per-question breakdown</h2>
        <PerQuestionSection perQuestion={data.per_question} />
      </div>
    </div>
  )
}
