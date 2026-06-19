import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { updateClass, deleteClass } from "@/api/assessments"
import { useClass, primeClass } from "@/features/class/useClass"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

export default function ClassSettings() {
  const { id } = useParams()
  const navigate = useNavigate()
  const cls = useClass(id)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [saving, setSaving] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (cls) {
      setName(cls.name ?? "")
      setDescription(cls.description ?? "")
    }
  }, [cls])

  async function handleSave(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Class name is required")
      return
    }
    setSaving(true)
    try {
      const updated = await updateClass(id, {
        name: name.trim(),
        description: description.trim(),
      })
      primeClass(updated) // refresh the shared cache so the panel/breadcrumb update
      toast.success("Class updated")
    } catch {
      toast.error("Failed to update class")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteClass(id)
      toast.success("Class deleted")
      navigate("/classes")
    } catch {
      toast.error("Failed to delete class")
      setDeleting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader title="Settings" description={cls?.name} />

      <form onSubmit={handleSave} className="max-w-lg space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="cls-name">Name</Label>
          <Input id="cls-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="cls-desc">Description (optional)</Label>
          <Textarea
            id="cls-desc"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={saving} className="min-h-[44px]">
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </form>

      {/* Danger zone */}
      <section className="max-w-lg space-y-3 rounded-xl border border-destructive/40 p-4">
        <div>
          <h2 className="text-sm font-semibold text-destructive">Delete this class</h2>
          <p className="text-sm text-muted-foreground">
            Permanently removes the class and its exams, subjects and rosters. This
            can't be undone.
          </p>
        </div>
        <Button variant="destructive" onClick={() => setDeleteOpen(true)} className="min-h-[40px]">
          Delete class
        </Button>
      </section>

      <Dialog open={deleteOpen} onOpenChange={(o) => !deleting && setDeleteOpen(o)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete class</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Delete <strong>{cls?.name}</strong> and everything in it? This can't be undone.
          </p>
          <DialogFooter showCloseButton>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Deleting…" : "Delete class"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
