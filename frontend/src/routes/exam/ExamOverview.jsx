import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ListChecks,
  Hash,
  Layers,
  CircleCheck,
  Pencil,
  Printer,
  ScanLine,
  ClipboardList,
  BarChart2,
  ChevronRight,
  AlertTriangle,
} from "lucide-react"
import { listQuestions } from "@/api/assessments"
import { useTest } from "@/features/test/useTest"
import { useClass } from "@/features/class/useClass"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageShell } from "@/components/ui/page-shell"
import { Skeleton } from "@/components/ui/skeleton"

const STATUS_VARIANT = { draft: "warning", ready: "success", closed: "neutral" }
const STATUS_LABELS = { draft: "Draft", ready: "Ready", closed: "Closed" }
const MODE_LABELS = {
  standard: "Standard",
  roster_prebubbled: "Roster",
  competitive: "Competitive",
}

function StatTile({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-4">
      <span className="grid size-16 shrink-0 place-items-center rounded-md border border-border bg-surface-2 text-muted-foreground">
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        <div className="mt-0.5 text-2xl font-semibold tabular-nums text-foreground">{value}</div>
      </div>
    </div>
  )
}

// The exam "home" — the hub that ties the lifecycle (questions → print → scan →
// results → analytics) together, mirroring the class Overview.
export default function ExamOverview() {
  const { testId } = useParams()
  const navigate = useNavigate()
  const test = useTest(testId)
  const cls = useClass(test?.class_group ?? null)
  const [qcount, setQcount] = useState(null)
  const [keyComplete, setKeyComplete] = useState(true)

  useEffect(() => {
    let cancelled = false
    listQuestions(testId)
      .then((d) => {
        if (cancelled) return
        const rows = d.results ?? d
        setQcount(rows.length)
        setKeyComplete(
          rows.length > 0 && rows.every((q) => (q.options ?? []).some((o) => o.is_correct)),
        )
      })
      .catch(() => {
        if (!cancelled) setQcount(0)
      })
    return () => {
      cancelled = true
    }
  }, [testId])

  const marksPer = test?.marking_scheme?.marks_per_correct ?? 1
  const totalMarks = qcount != null ? +(qcount * marksPer).toFixed(2) : null

  const actions = [
    { label: "Edit questions", desc: "Add or change questions & answer key", icon: Pencil, to: `/tests/${testId}/questions` },
    { label: "Generate & print", desc: "Produce one OMR sheet per student", icon: Printer, to: `/tests/${testId}/sheets` },
    { label: "Scan sheets", desc: "Upload filled sheets to auto-grade", icon: ScanLine, to: `/tests/${testId}/scan` },
    { label: "Results", desc: "Grades, report cards & sharing", icon: ClipboardList, to: `/tests/${testId}/results` },
    { label: "Analytics", desc: "Item analysis & class insights", icon: BarChart2, to: `/tests/${testId}/analytics` },
  ]

  const ready = test != null && qcount != null

  return (
    <PageShell>
      {/* Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-3xl font-bold tracking-tight">{test?.title ?? "Exam"}</h1>
          {test && (
            <Badge variant={STATUS_VARIANT[test.status] ?? "neutral"}>
              {STATUS_LABELS[test.status] ?? test.status}
            </Badge>
          )}
        </div>
        <p className="mt-2 text-muted-foreground">
          {[cls?.name, test?.subject].filter(Boolean).join(" · ") || "No subject"}
        </p>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {!ready ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-md" />
          ))
        ) : (
          <>
            <StatTile icon={ListChecks} label="Questions" value={qcount} />
            <StatTile icon={Hash} label="Total marks" value={totalMarks} />
            <StatTile
              icon={Layers}
              label="Mode"
              value={<span className="text-base font-medium">{MODE_LABELS[test.mode] ?? test.mode}</span>}
            />
            <StatTile
              icon={CircleCheck}
              label="Attempt"
              value={<span className="tabular-nums">#{test.attempt_number}</span>}
            />
          </>
        )}
      </div>

      {/* Answer-key / empty nudges */}
      {ready && qcount === 0 && (
        <div className="rounded-xl border border-dashed border-border p-8 text-center">
          <ListChecks className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
          <p className="mt-3 font-medium">No questions yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Add questions and mark the correct answers before you generate sheets.
          </p>
          <Button className="mt-4" onClick={() => navigate(`/tests/${testId}/questions`)}>
            <Pencil className="size-4" aria-hidden="true" /> Add questions
          </Button>
        </div>
      )}
      {ready && qcount > 0 && !keyComplete && (
        <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
          <span>
            Some questions have no correct answer set — grading will skip them.{" "}
            <button
              type="button"
              onClick={() => navigate(`/tests/${testId}/questions`)}
              className="font-medium text-primary hover:underline"
            >
              Fix the answer key
            </button>
          </span>
        </div>
      )}

      {/* Quick actions */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Lifecycle</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              onClick={() => navigate(a.to)}
              className="flex min-h-[40px] items-center gap-3 rounded-xl border border-border bg-surface-1 p-4 text-left motion-safe-card outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                <a.icon className="size-4.5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{a.label}</span>
                <span className="block truncate text-xs text-muted-foreground">{a.desc}</span>
              </span>
              <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            </button>
          ))}
        </div>
      </section>
    </PageShell>
  )
}
