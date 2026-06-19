import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { createOrg } from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// Org-first onboarding (Supabase-style "New organization"). A user with no
// organization lands here before they can use the app. On success the new org
// becomes active and we go to the org home (Classes).
export default function NewOrganization() {
  const navigate = useNavigate()
  const { setActiveOrg, refreshOrgs } = useOrg()
  const [name, setName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Organization name is required")
      return
    }
    setSubmitting(true)
    try {
      const org = await createOrg(name.trim())
      await refreshOrgs({ force: true })
      setActiveOrg(String(org.id))
      toast.success("Organization created")
      navigate("/classes")
    } catch {
      toast.error("Could not create organization")
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <p className="text-lg font-bold tracking-tight text-primary">DoxaEd OMR</p>
          <h1 className="mt-4 text-2xl font-bold tracking-tight">Create your organization</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your classes, exams, students and team all live inside an organization.
            You can rename it or create more later.
          </p>
        </div>
        <form
          onSubmit={handleCreate}
          className="space-y-4 rounded-2xl border border-border bg-surface-1 p-6"
        >
          <div className="space-y-1.5">
            <Label htmlFor="org-name">Organization name</Label>
            <Input
              id="org-name"
              placeholder="e.g. Springfield High School"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={submitting || !name.trim()} className="min-h-[44px] w-full">
            {submitting ? "Creating…" : "Create organization"}
          </Button>
        </form>
      </div>
    </div>
  )
}
