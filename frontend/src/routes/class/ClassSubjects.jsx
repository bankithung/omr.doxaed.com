import { useEffect, useState, useCallback } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { X as XIcon, BookOpen } from "lucide-react"
import { listSubjects, createSubject, deleteSubject } from "@/api/subjects"
import { useClass } from "@/features/class/useClass"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"

export default function ClassSubjects() {
  const { id } = useParams()
  const cls = useClass(id)
  // Subjects are class-wide. When viewing a SECTION, manage the PARENT class's
  // subjects so they're shared across the class and every section.
  const subjectsClassId = cls?.parent ?? id
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState("")
  const [adding, setAdding] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await listSubjects(subjectsClassId)
      setSubjects(d.results ?? d)
    } catch {
      toast.error("Failed to load subjects")
    } finally {
      setLoading(false)
    }
  }, [subjectsClassId])

  useEffect(() => {
    load()
  }, [load])

  async function add(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Subject name is required")
      return
    }
    setAdding(true)
    try {
      await createSubject({ class_group: subjectsClassId, name: name.trim() })
      setName("")
      toast.success("Subject added")
      load()
    } catch (err) {
      toast.error(err?.response?.data?.name?.[0] || err?.response?.data?.detail || "Failed to add subject")
    } finally {
      setAdding(false)
    }
  }

  async function remove() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteSubject(deleteTarget.id)
      toast.success("Subject removed")
      setDeleteTarget(null)
      load()
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to remove subject")
    } finally {
      setDeleting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader title="Subjects" description={cls?.name} />
      <p className="text-sm text-muted-foreground">
        Subjects let you tag exams (e.g. Physics, Chemistry) so results group by subject.
        They're shared across the whole class and every section.
      </p>

      <form onSubmit={add} className="flex items-center gap-2 sm:max-w-md">
        <Input
          placeholder="e.g. Mathematics"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1"
          aria-label="New subject name"
        />
        <Button type="submit" size="sm" className="min-h-[40px]" disabled={adding}>
          {adding ? "Adding…" : "Add subject"}
        </Button>
      </form>

      {loading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : subjects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-10 text-center">
          <BookOpen className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
          <p className="mt-3 font-medium">No subjects yet</p>
          <p className="mt-1 text-sm text-muted-foreground">Add subjects to tag this class's exams.</p>
        </div>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface-1">
          {subjects.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-md bg-primary/10 text-xs font-bold text-primary">
                  {(s.name?.[0] ?? "?").toUpperCase()}
                </span>
                <span className="truncate font-medium">{s.name}</span>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Remove ${s.name}`}
                onClick={() => setDeleteTarget(s)}
              >
                <XIcon className="size-4" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Dialog open={!!deleteTarget} onOpenChange={(o) => !deleting && !o && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove subject</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Remove <strong>{deleteTarget?.name}</strong>? Existing exams keep their subject text.
          </p>
          <DialogFooter showCloseButton>
            <Button variant="destructive" onClick={remove} disabled={deleting}>
              {deleting ? "Removing…" : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
