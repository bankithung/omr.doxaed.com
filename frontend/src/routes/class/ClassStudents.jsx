import { useEffect, useState, useCallback } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { Plus, Users } from "lucide-react"
import { listClasses, createClass } from "@/api/assessments"
import { listRosters, createRoster, listStudents, addStudent } from "@/api/omr"
import { useClass } from "@/features/class/useClass"
import { useOrg } from "@/org/OrgContext"
import { childKindLabel } from "@/features/class/typePresets"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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

const NEW = "__new__"

// Each group (class or section) keeps one hidden roster that holds its students.
async function rosterForGroup(groupId) {
  const rs = await listRosters({ class_group: groupId })
  const list = rs.results ?? rs
  if (list.length) return list[0]
  return createRoster({ name: "Students", class_group: Number(groupId) })
}

function AddStudentDialog({ classId, sections, childLabel, onClose, onAdded }) {
  const [fullName, setFullName] = useState("")
  const [roll, setRoll] = useState("")
  const [target, setTarget] = useState(sections[0] ? String(sections[0].id) : String(classId))
  const [newName, setNewName] = useState("")
  const [saving, setSaving] = useState(false)
  const lower = childLabel.toLowerCase()

  async function save(e) {
    e.preventDefault()
    if (!roll.trim()) {
      toast.error("Roll number is required")
      return
    }
    if (target === NEW && !newName.trim()) {
      toast.error(`${childLabel} name is required`)
      return
    }
    setSaving(true)
    try {
      let groupId = target
      if (target === NEW) {
        const sec = await createClass({
          name: newName.trim(),
          parent: Number(classId),
          kind_label: childLabel,
        })
        groupId = sec.id
      }
      const roster = await rosterForGroup(groupId)
      await addStudent({ roster: roster.id, full_name: fullName.trim(), roll_number: roll.trim() })
      toast.success("Student added")
      onAdded()
    } catch (err) {
      toast.error(
        err?.response?.data?.roll_number?.[0] || err?.response?.data?.detail || "Failed to add student",
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add student</DialogTitle>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="s-name">Full name (optional)</Label>
              <Input id="s-name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="e.g. Asha Devi" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="s-roll">Roll number</Label>
              <Input id="s-roll" value={roll} onChange={(e) => setRoll(e.target.value)} placeholder="e.g. 101" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="s-section">{childLabel}</Label>
            <Select value={target} onValueChange={setTarget}>
              <SelectTrigger id="s-section" className="min-h-[40px] w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={String(classId)}>Whole class (no {lower})</SelectItem>
                {sections.map((s) => (
                  <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                ))}
                <SelectItem value={NEW}>＋ New {lower}…</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {target === NEW && (
            <div className="space-y-1.5">
              <Label htmlFor="new-sec">New {lower} name</Label>
              <Input id="new-sec" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={`e.g. ${childLabel} A`} />
            </div>
          )}
          <DialogFooter showCloseButton>
            <Button type="submit" disabled={saving}>{saving ? "Adding…" : "Add student"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function ClassStudents() {
  const { id } = useParams()
  const cls = useClass(id)
  const { activeOrg } = useOrg() ?? {}
  const childLabel = childKindLabel(activeOrg?.type, cls?.kind_label)

  const [sections, setSections] = useState([])
  const [blocks, setBlocks] = useState([])
  const [loading, setLoading] = useState(true)
  const [addOpen, setAddOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const secD = await listClasses({ parent: id })
      const secs = secD.results ?? secD
      setSections(secs)
      const nodes = [
        { id: Number(id), name: "Direct (no section)", isClass: true },
        ...secs.map((s) => ({ id: s.id, name: s.name, kind: s.kind_label })),
      ]
      const withStudents = await Promise.all(
        nodes.map(async (n) => {
          const rs = await listRosters({ class_group: n.id })
          const roster = (rs.results ?? rs)[0]
          let students = []
          if (roster) {
            const sd = await listStudents(roster.id)
            students = sd.results ?? sd
          }
          return { ...n, students }
        }),
      )
      setBlocks(withStudents)
    } catch {
      toast.error("Failed to load students")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const total = blocks.reduce((s, b) => s + b.students.length, 0)
  const visible = blocks.filter((b) => !b.isClass || b.students.length > 0)
  const lower = childLabel.toLowerCase()

  return (
    <PageShell>
      <PageHeader
        title="Students"
        description={cls?.name}
        actions={
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="size-4" aria-hidden="true" /> Add student
          </Button>
        }
      />

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
        </div>
      ) : total === 0 && sections.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-10 text-center">
          <Users className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
          <p className="mt-3 font-medium">No students yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Add students into {lower}s — you can create a {lower} right as you add the first one.
          </p>
          <Button className="mt-4" onClick={() => setAddOpen(true)}>
            <Plus className="size-4" aria-hidden="true" /> Add student
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          {visible.map((b) => (
            <section key={b.id} className="overflow-hidden rounded-xl border border-border bg-surface-1">
              <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
                <div className="flex items-center gap-2">
                  <p className="font-semibold">{b.name}</p>
                  {b.kind && <span className="text-xs text-muted-foreground">{b.kind}</span>}
                </div>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {b.students.length} student{b.students.length === 1 ? "" : "s"}
                </span>
              </div>
              {b.students.length === 0 ? (
                <p className="px-4 py-4 text-sm text-muted-foreground">No students in this {lower} yet.</p>
              ) : (
                <ul className="divide-y divide-border">
                  {b.students.map((s) => (
                    <li key={s.id} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="w-12 shrink-0 font-mono text-xs font-medium tabular-nums">{s.roll_number}</span>
                      <span className="truncate">
                        {s.full_name || <span className="italic text-muted-foreground">—</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}

      {addOpen && (
        <AddStudentDialog
          classId={id}
          sections={sections}
          childLabel={childLabel}
          onClose={() => setAddOpen(false)}
          onAdded={() => {
            setAddOpen(false)
            load()
          }}
        />
      )}
    </PageShell>
  )
}
