import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { useOrg } from "@/org/OrgContext"
import { createOrg } from "@/api/orgs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { EmptyState } from "@/components/ui/empty-state"

const ROLE_LABELS = { admin: "Admin", member: "Member", viewer: "Viewer" }

export default function Organizations() {
  const { orgs, refreshOrgs } = useOrg()
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [orgName, setOrgName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setLoading(true)
    refreshOrgs().finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function openDialog() {
    setOrgName("")
    setDialogOpen(true)
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!orgName.trim()) {
      toast.error("Organization name is required")
      return
    }
    setSubmitting(true)
    try {
      await createOrg(orgName.trim())
      toast.success("Organization created")
      setDialogOpen(false)
      await refreshOrgs()
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data?.name?.[0] || "Failed to create organization"
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Organizations</h1>
          <p className="text-sm text-muted-foreground">Manage your organizations and teams</p>
        </div>
        <Button onClick={openDialog}>Create organization</Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : orgs.length === 0 ? (
        <EmptyState
          title="No organizations yet"
          description="Create an organization to collaborate with your team."
          action={<Button onClick={openDialog}>Create organization</Button>}
        />
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Your role</TableHead>
                <TableHead className="w-28 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orgs.map((org) => (
                <TableRow key={org.id}>
                  <TableCell className="font-medium">{org.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {ROLE_LABELS[org.role] ?? org.role}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/organizations/${org.id}/members`}>Members</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create organization</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="org-name">Organization name</Label>
              <Input
                id="org-name"
                placeholder="e.g. Acme School"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                autoFocus
              />
            </div>
            <DialogFooter showCloseButton>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
