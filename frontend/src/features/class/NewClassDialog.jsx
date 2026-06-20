import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Plus, X as XIcon } from "lucide-react"
import { createClass } from "@/api/assessments"
import { createSubject } from "@/api/subjects"
import { getMembers, createClassGrant } from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { childKindLabel } from "@/features/class/typePresets"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"

// A reusable "add chips" field: type a name + Add → removable chips.
function ChipAdder({ label, hint, placeholder, items, onAdd, onRemove }) {
  const [value, setValue] = useState("")
  function add() {
    const v = value.trim()
    if (v && !items.includes(v)) onAdd(v)
    setValue("")
  }
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      <div className="flex gap-2">
        <Input
          value={value}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              add()
            }
          }}
          className="flex-1"
        />
        <Button type="button" variant="outline" size="sm" className="min-h-[40px]" onClick={add}>
          <Plus className="size-4" aria-hidden="true" /> Add
        </Button>
      </div>
      {items.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {items.map((it) => (
            <Badge key={it} variant="neutral" className="gap-1 pr-1">
              {it}
              <button
                type="button"
                onClick={() => onRemove(it)}
                aria-label={`Remove ${it}`}
                className="rounded-sm p-0.5 hover:bg-muted-foreground/20"
              >
                <XIcon className="size-3" aria-hidden="true" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

// Create a class with optional sections, subjects, and teacher assignments — all
// optional and addable later, but handy to set up at once.
export default function NewClassDialog({ topLabel, onClose, onCreated }) {
  const { activeOrg } = useOrg() ?? {}
  const orgId = activeOrg?.id
  const childLabel = childKindLabel(activeOrg?.type, topLabel)

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [sections, setSections] = useState([])
  const [subjects, setSubjects] = useState([])
  const [members, setMembers] = useState([])
  const [teacherIds, setTeacherIds] = useState([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!orgId) return
    getMembers(orgId)
      .then((d) => setMembers(d.results ?? d))
      .catch(() => setMembers([]))
  }, [orgId])

  // Members you can assign — exclude yourself (the creator/admin already has access).
  const assignable = members.filter((m) => m.user_id !== activeOrg?.owner)

  function toggleTeacher(userId) {
    setTeacherIds((ids) =>
      ids.includes(userId) ? ids.filter((x) => x !== userId) : [...ids, userId],
    )
  }

  async function save(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error(`${topLabel} name is required`)
      return
    }
    setSaving(true)
    try {
      const cls = await createClass({
        name: name.trim(),
        description: description.trim(),
        kind_label: topLabel,
      })
      // Sections (sub-groups), subjects, and teacher grants — best-effort each.
      for (const s of sections) {
        await createClass({ name: s, parent: cls.id, kind_label: childLabel })
      }
      for (const sub of subjects) {
        await createSubject({ class_group: cls.id, name: sub })
      }
      for (const userId of teacherIds) {
        await createClassGrant({ user: userId, class_group: cls.id, all_subjects: true })
      }
      const extras = []
      if (sections.length) extras.push(`${sections.length} ${childLabel.toLowerCase()}${sections.length === 1 ? "" : "s"}`)
      if (subjects.length) extras.push(`${subjects.length} subject${subjects.length === 1 ? "" : "s"}`)
      if (teacherIds.length) extras.push(`${teacherIds.length} teacher${teacherIds.length === 1 ? "" : "s"}`)
      toast.success(`${topLabel} created${extras.length ? ` with ${extras.join(", ")}` : ""}`)
      onCreated(cls)
    } catch (err) {
      toast.error(err?.response?.data?.detail || `Failed to create ${topLabel.toLowerCase()}`)
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New {topLabel.toLowerCase()}</DialogTitle>
          <DialogDescription>
            Set it up now or add {childLabel.toLowerCase()}s, subjects and teachers later.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="cls-name">{topLabel} name</Label>
            <Input
              id="cls-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`e.g. ${topLabel} 8`}
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cls-desc">Description (optional)</Label>
            <Input
              id="cls-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Short description"
            />
          </div>

          <ChipAdder
            label={`${childLabel}s (optional)`}
            hint={`Add ${childLabel.toLowerCase()}s — students and exams can be scoped to each.`}
            placeholder={`e.g. ${childLabel} A`}
            items={sections}
            onAdd={(v) => setSections((s) => [...s, v])}
            onRemove={(v) => setSections((s) => s.filter((x) => x !== v))}
          />

          <ChipAdder
            label="Subjects (optional)"
            hint="Tag exams by subject (e.g. Maths, Science)."
            placeholder="e.g. Mathematics"
            items={subjects}
            onAdd={(v) => setSubjects((s) => [...s, v])}
            onRemove={(v) => setSubjects((s) => s.filter((x) => x !== v))}
          />

          <div className="space-y-1.5">
            <Label>Assign teachers (optional)</Label>
            {assignable.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No other members to assign yet. Invite people in Members first.
              </p>
            ) : (
              <div className="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-border p-2">
                {assignable.map((m) => {
                  const uid = m.user_id ?? m.id
                  return (
                    <label
                      key={uid}
                      className="flex min-h-[36px] cursor-pointer items-center gap-2 rounded-md px-2 py-1 hover:bg-muted"
                    >
                      <Checkbox
                        checked={teacherIds.includes(uid)}
                        onCheckedChange={() => toggleTeacher(uid)}
                      />
                      <span className="truncate text-sm">{m.email}</span>
                    </label>
                  )
                })}
              </div>
            )}
          </div>

          <DialogFooter showCloseButton>
            <Button type="submit" disabled={saving}>
              {saving ? "Creating…" : `Create ${topLabel.toLowerCase()}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
