import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { BuildingIcon } from "lucide-react"
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
import { DataTable } from "@/components/ui/DataTable"
import { Badge } from "@/components/ui/badge"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

const ROLE_LABELS = { admin: "Admin", member: "Member", viewer: "Viewer" }
const ROLE_VARIANT = { admin: "info", member: "neutral", viewer: "neutral" }

const COLUMNS = [
  {
    key: "name",
    header: "Name",
    cell: (org) => (
      <Link
        to={`/organizations/${org.id}/members`}
        className="font-medium hover:text-primary hover:underline"
      >
        {org.name}
      </Link>
    ),
  },
  {
    key: "role",
    header: "Your role",
    cell: (org) => (
      <Badge variant={ROLE_VARIANT[org.role] ?? "neutral"}>
        {ROLE_LABELS[org.role] ?? org.role}
      </Badge>
    ),
  },
  {
    key: "actions",
    header: "",
    mobileLabel: "",
    cell: (org) => (
      <Button asChild variant="outline" size="sm" className="min-h-[40px]">
        <Link to={`/organizations/${org.id}/members`}>Members</Link>
      </Button>
    ),
    className: "w-28 text-right",
  },
]

export default function Organizations() {
  const { orgs, refreshOrgs } = useOrg()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [orgName, setOrgName] = useState("")
  const [submitting, setSubmitting] = useState(false)

  function loadOrgs() {
    setLoading(true)
    setError(false)
    refreshOrgs({ force: true })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadOrgs()
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
      await refreshOrgs({ force: true })
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.name?.[0] ||
        "Failed to create organization"
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <PageShell>
      <PageHeader
        title="Organizations"
        description="Manage your organizations and teams"
        actions={<Button onClick={openDialog}>Create organization</Button>}
      />

      {!loading && !error && orgs.length > 0 && (
        <div className="-mb-4">
          <Badge variant="neutral" className="tabular">
            {orgs.length}{" "}
            {orgs.length === 1 ? "organization" : "organizations"}
          </Badge>
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={orgs}
        getRowKey={(org) => org.id}
        loading={loading}
        error={error}
        onRetry={loadOrgs}
        empty={{
          icon: BuildingIcon,
          title: "No organizations yet",
          description: "Create an organization to collaborate with your team.",
          action: <Button onClick={openDialog}>Create organization</Button>,
        }}
      />

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
    </PageShell>
  )
}
