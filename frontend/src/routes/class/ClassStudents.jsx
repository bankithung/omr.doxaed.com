import { useEffect, useState, useCallback } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { Plus, Users, Search } from "lucide-react"
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
import { Badge } from "@/components/ui/badge"

const NEW = "__new__"

// Each group (class or section) keeps one hidden roster that holds its students.
async function rosterForGroup(groupId) {
  const rs = await listRosters({ class_group: groupId })
  const list = rs.results ?? rs
  if (list.length) return list[0]
  return createRoster({ name: "Students", class_group: groupId })
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
          parent: classId,
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
  const [filter, setFilter] = useState("all")
  const [query, setQuery] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const secD = await listClasses({ parent: id })
      const secs = secD.results ?? secD
      setSections(secs)
      const nodes = [
        { id: id, name: "Direct (no section)", isClass: true },
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

  const allStudents = blocks.flatMap((b) =>
    b.students.map((s) => ({ ...s, _section: b.isClass ? null : b.name, _sid: String(b.id) })),
  )
  const sectionOptions = blocks.map((b) => ({
    value: String(b.id),
    label: b.isClass ? "Direct (no section)" : b.name,
  }))
  const q = query.trim().toLowerCase()
  const filtered = allStudents
    .filter((s) => filter === "all" || s._sid === filter)
    .filter(
      (s) =>
        !q ||
        s.full_name?.toLowerCase().includes(q) ||
        String(s.roll_number ?? "").toLowerCase().includes(q),
    )
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
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : allStudents.length === 0 && sections.length === 0 ? (
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
        <div className="space-y-3">
          {/* Search + filter by section */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-full sm:max-w-xs">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                placeholder="Search by name or roll…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
                aria-label="Search students"
              />
            </div>
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="min-h-[40px] w-full sm:w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All {lower}s</SelectItem>
                {sectionOptions.map((o) => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="ml-auto text-xs text-muted-foreground tabular-nums">
              {filtered.length} student{filtered.length === 1 ? "" : "s"}
            </span>
          </div>

          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">No students match your filters.</p>
          ) : (
            <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface-1">
              {filtered.map((s) => (
                <li key={s.id} className="flex items-center gap-3 px-4 py-2.5">
                  <span className="w-12 shrink-0 font-mono text-xs font-medium tabular-nums">{s.roll_number}</span>
                  <span className="min-w-0 flex-1 truncate">
                    {s.full_name || <span className="italic text-muted-foreground">—</span>}
                  </span>
                  {s._section && <Badge variant="neutral">{s._section}</Badge>}
                </li>
              ))}
            </ul>
          )}
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
