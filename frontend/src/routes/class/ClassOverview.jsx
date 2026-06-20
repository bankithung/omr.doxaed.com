import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { FileText, Users, BookOpen, Layers, Plus } from "lucide-react"
import { listTests, listClasses } from "@/api/assessments"
import { listSubjects } from "@/api/subjects"
import { listRosters } from "@/api/omr"
import { useClass } from "@/features/class/useClass"
import { useOrg } from "@/org/OrgContext"
import { childKindLabel, pluralize } from "@/features/class/typePresets"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageShell } from "@/components/ui/page-shell"
import { Skeleton } from "@/components/ui/skeleton"
import AddSectionDialog from "@/features/class/AddSectionDialog"

// A Supabase-style stat tile: a 64px icon tile + label + big mono number.
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

// The class "project" Overview — the Supabase project-dashboard equivalent.
export default function ClassOverview() {
  const { id } = useParams()
  const navigate = useNavigate()
  const cls = useClass(id)
  // When viewing a section, show its parent class as context above the title.
  const parentCls = useClass(cls?.parent ?? null)
  const { activeOrg } = useOrg() ?? {}
  const childLabel = childKindLabel(activeOrg?.type, cls?.kind_label)
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [sections, setSections] = useState([])
  const [addSecOpen, setAddSecOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  // Counts span the whole subtree — exams and students can live on the class
  // itself OR on any of its sections, so summing only the class would lie.
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const secD = await listClasses({ parent: id })
      const secs = secD.results ?? secD
      setSections(secs)
      const groups = [
        { id: id, label: null },
        ...secs.map((s) => ({ id: s.id, label: s.name })),
      ]
      const [perGroupTests, perGroupRosters, subjectsD] = await Promise.all([
        Promise.all(
          groups.map(async (g) => {
            const d = await listTests(g.id)
            return (d.results ?? d).map((t) => ({ ...t, _section: g.label }))
          }),
        ),
        Promise.all(
          groups.map(async (g) => {
            const d = await listRosters({ class_group: g.id })
            return d.results ?? d
          }),
        ),
        listSubjects(id),
      ])
      const tests = perGroupTests.flat()
      const rosters = perGroupRosters.flat()
      const subjects = subjectsD.results ?? subjectsD
      const students = rosters.reduce(
        (sum, r) => sum + (r.student_count ?? r.students_count ?? 0),
        0,
      )
      setStats({
        exams: tests.length,
        students,
        subjects: subjects.length,
        sections: secs.length,
      })
      setRecent(
        [...tests]
          .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
          .slice(0, 5),
      )
    } catch {
      setStats({ exams: 0, students: 0, subjects: 0, sections: 0 })
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  return (
    <PageShell>
      {/* Header */}
      <div>
        {parentCls && (
          <Link
            to={`/classes/${parentCls.id}`}
            className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            {parentCls.name}
            <span aria-hidden="true">›</span>
          </Link>
        )}
        <h1 className="text-3xl font-bold tracking-tight">{cls?.name ?? "Class"}</h1>
        <p className="mt-2 text-muted-foreground">{cls?.description || "No description"}</p>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {loading || !stats ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-md" />
          ))
        ) : (
          <>
            <StatTile icon={FileText} label="Exams" value={stats.exams} />
            <StatTile icon={Users} label="Students" value={stats.students} />
            <StatTile icon={Layers} label={pluralize(childLabel)} value={stats.sections} />
            <StatTile icon={BookOpen} label="Subjects" value={stats.subjects} />
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => navigate(`/classes/${id}/tests/new`)}>
          <Plus className="size-4" aria-hidden="true" /> New exam
        </Button>
        <Button variant="outline" onClick={() => navigate(`/classes/${id}/students`)}>
          Add students
        </Button>
        <Button variant="outline" onClick={() => navigate(`/classes/${id}/subjects`)}>
          Manage subjects
        </Button>
      </div>

      {/* Sections (sub-groups) — shown here instead of a separate page */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">{pluralize(childLabel)}</h2>
          <Button
            variant="outline"
            size="sm"
            className="min-h-[36px]"
            onClick={() => setAddSecOpen(true)}
          >
            <Plus className="size-4" aria-hidden="true" /> Add {childLabel.toLowerCase()}
          </Button>
        </div>
        {loading ? (
          <Skeleton className="h-20 w-full rounded-lg" />
        ) : sections.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center">
            <p className="text-sm text-muted-foreground">
              No {pluralize(childLabel).toLowerCase()} yet. Add one to scope students and exams.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sections.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => navigate(`/classes/${s.id}`)}
                className="group flex items-center gap-3 rounded-xl border border-border bg-surface-1 p-4 text-left transition-colors hover:border-primary/50 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-sm font-bold text-primary">
                  {(s.name?.[0] ?? "?").toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-semibold group-hover:text-primary">{s.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{s.kind_label || childLabel}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Recent exams */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Recent exams</h2>
          <Link
            to={`/classes/${id}/exams`}
            className="text-xs font-medium text-primary hover:underline"
          >
            View all
          </Link>
        </div>
        {loading ? (
          <Skeleton className="h-24 w-full rounded-lg" />
        ) : recent.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">No exams yet.</p>
            <Button className="mt-3" onClick={() => navigate(`/classes/${id}/tests/new`)}>
              Create your first exam
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
            {recent.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-medium">{t.title}</p>
                    {t._section && <Badge variant="neutral">{t._section}</Badge>}
                  </div>
                  <p className="truncate text-xs text-muted-foreground">
                    {t.subject || "No subject"} · attempt #{t.attempt_number}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="min-h-[40px]"
                  onClick={() => navigate(`/tests/${t.id}/sheets`)}
                >
                  Generate
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {addSecOpen && (
        <AddSectionDialog
          classId={id}
          childLabel={childLabel}
          onClose={() => setAddSecOpen(false)}
          onCreated={() => {
            setAddSecOpen(false)
            load()
          }}
        />
      )}
    </PageShell>
  )
}
