import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { createRoster } from "@/api/omr"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

// Dedicated "Create roster" page (replaces the modal on /rosters). On success it
// lands on the new roster so the user can add students next.
export default function NewRoster() {
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Roster name is required")
      return
    }
    setSubmitting(true)
    try {
      const created = await createRoster({ name: name.trim() })
      toast.success("Roster created")
      navigate(`/rosters/${created.id}`)
    } catch {
      toast.error("Failed to create roster")
      setSubmitting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader
        title="Create roster"
        description="A student list for OMR sheet generation."
        actions={
          <Button
            variant="outline"
            className="min-h-[40px]"
            onClick={() => navigate("/rosters")}
          >
            Cancel
          </Button>
        }
      />

      <form onSubmit={handleCreate} className="max-w-lg space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="roster-name">Name</Label>
          <Input
            id="roster-name"
            placeholder="e.g. Class 10A"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <Button type="submit" disabled={submitting || !name.trim()} className="min-h-[44px]">
            {submitting ? "Creating…" : "Create roster"}
          </Button>
        </div>
      </form>
    </PageShell>
  )
}
