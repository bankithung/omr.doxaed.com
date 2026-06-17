import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { listResults } from "@/api/scan"
import { Button } from "@/components/ui/button"
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

function StudentResultRow({ result }) {
  const [expanded, setExpanded] = useState(false)
  const responses = result.responses ?? result.question_responses ?? []

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={() => setExpanded((v) => !v)}
      >
        <TableCell className="font-mono text-sm">
          {result.student?.roll_number ?? result.omr_sheet ?? "—"}
        </TableCell>
        <TableCell>
          {result.student?.name ?? result.student?.full_name ?? "—"}
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
        <TableCell className="text-right text-xs text-muted-foreground">
          {expanded ? "▲ collapse" : "▼ details"}
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

export default function Results() {
  const { testId } = useParams()
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)

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

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Results</h1>
          <p className="text-sm text-muted-foreground">Test #{testId}</p>
        </div>
        <div className="flex gap-2">
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
                    results.reduce((s, r) => s + (r.score ?? 0), 0) / results.length
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
                  <StudentResultRow key={r.id} result={r} />
                ))}
              </TableBody>
            </Table>
          </div>

          <p className="mt-3 text-xs text-muted-foreground">
            Click a row to expand per-question responses.
          </p>
        </>
      )}
    </div>
  )
}
