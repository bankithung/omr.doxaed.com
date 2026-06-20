import { useState } from "react"
import { toast } from "sonner"
import { createClass } from "@/api/assessments"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"

// Add one section (a child ClassGroup) to a class. Subjects are class-wide, so a
// section only needs a name — students and exams get scoped to it afterwards.
export default function AddSectionDialog({ classId, childLabel, onClose, onCreated }) {
  const [name, setName] = useState("")
  const [saving, setSaving] = useState(false)
  const label = childLabel || "Section"

  async function save(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error(`${label} name is required`)
      return
    }
    setSaving(true)
    try {
      const sec = await createClass({ name: name.trim(), parent: classId, kind_label: label })
      toast.success(`${label} added`)
      onCreated(sec)
    } catch (err) {
      toast.error(err?.response?.data?.detail || `Failed to add ${label.toLowerCase()}`)
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New {label.toLowerCase()}</DialogTitle>
          <DialogDescription>
            Students and exams can be scoped to this {label.toLowerCase()}. Subjects stay shared across the class.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="section-name">{label} name</Label>
            <Input
              id="section-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`e.g. ${label} A`}
              autoFocus
            />
          </div>
          <DialogFooter showCloseButton>
            <Button type="submit" disabled={saving}>
              {saving ? "Adding…" : `Add ${label.toLowerCase()}`}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
