import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { createClass } from "@/api/assessments"
import { listFolders } from "@/api/folders"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

// Sentinel value for the "No folder" option (Radix Select disallows empty values).
const NO_FOLDER = "__none__"

// Dedicated "Create class" page (replaces the modal on /classes). On success it
// lands on the new class so the user can set it up right away.
export default function NewClass() {
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [folderId, setFolderId] = useState(NO_FOLDER)
  const [folders, setFolders] = useState([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    // Folders are optional + additive — silently ignore failures.
    listFolders()
      .then((data) => setFolders(data.results ?? data))
      .catch(() => setFolders([]))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Class name is required")
      return
    }
    setSubmitting(true)
    try {
      const payload = { name: name.trim(), description: description.trim() }
      if (folderId !== NO_FOLDER) payload.folder = Number(folderId)
      const created = await createClass(payload)
      toast.success("Class created")
      navigate(`/classes/${created.id}`)
    } catch {
      toast.error("Failed to create class")
      setSubmitting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader
        title="Create class"
        description="Add a new class group."
        actions={
          <Button
            variant="outline"
            className="min-h-[40px]"
            onClick={() => navigate("/classes")}
          >
            Cancel
          </Button>
        }
      />

      <form onSubmit={handleCreate} className="max-w-lg space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="class-name">Name</Label>
          <Input
            id="class-name"
            placeholder="e.g. Class 8A"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="class-desc">Description (optional)</Label>
          <Textarea
            id="class-desc"
            placeholder="Short description of this class"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        {folders.length > 0 && (
          <div className="space-y-1.5">
            <Label htmlFor="class-folder">Folder (optional)</Label>
            <Select value={folderId} onValueChange={setFolderId}>
              <SelectTrigger id="class-folder" className="min-h-[40px] w-full sm:max-w-sm">
                <SelectValue placeholder="No folder" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_FOLDER}>No folder</SelectItem>
                {folders.map((f) => (
                  <SelectItem key={f.id} value={String(f.id)}>
                    {f.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="flex gap-2">
          <Button type="submit" disabled={submitting || !name.trim()} className="min-h-[44px]">
            {submitting ? "Creating…" : "Create class"}
          </Button>
        </div>
      </form>
    </PageShell>
  )
}
