import { useEffect, useState, useCallback } from "react"
import { toast } from "sonner"
import { ShieldIcon } from "lucide-react"
import { useOrg } from "@/org/OrgContext"
import { getAudit } from "@/api/orgs"
import { DataTable } from "@/components/ui/DataTable"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

function formatDate(isoString) {
  if (!isoString) return "—"
  return new Date(isoString).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const COLUMNS = [
  {
    key: "actor",
    header: "Actor",
    cell: (entry) =>
      entry.actor_email ?? (
        <span className="italic text-muted-foreground">system</span>
      ),
  },
  {
    key: "action",
    header: "Action",
    cell: (entry) => (
      <span className="font-mono text-xs">{entry.action}</span>
    ),
  },
  {
    key: "target",
    header: "Target",
    cell: (entry) => (
      <span className="text-muted-foreground">
        {entry.target_type ? (
          <>
            {entry.target_type}
            {entry.target_id != null && (
              <span className="font-mono text-xs"> #{entry.target_id}</span>
            )}
          </>
        ) : (
          "—"
        )}
      </span>
    ),
  },
  {
    key: "when",
    header: "When",
    cell: (entry) => (
      <span className="tabular text-muted-foreground">
        {formatDate(entry.created_at)}
      </span>
    ),
    className: "whitespace-nowrap",
  },
]

export default function OrgAudit() {
  const { activeOrg } = useOrg()
  const orgId = activeOrg?.id
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const org = activeOrg

  const fetchAudit = useCallback(() => {
    setLoading(true)
    setError(false)
    getAudit(orgId)
      .then((data) => setEntries(data.results ?? data))
      .catch(() => {
        setError(true)
        toast.error("Failed to load audit log")
      })
      .finally(() => setLoading(false))
  }, [orgId])

  useEffect(() => {
    fetchAudit()
  }, [fetchAudit])

  return (
    <PageShell>
      <PageHeader
        title="Audit log"
        description={`Events for ${org?.name ?? "this organization"}`}
      />

      {!loading && !error && entries.length > 0 && (
        <div className="-mb-4">
          <span className="text-sm text-muted-foreground">
            <span className="tabular font-medium text-foreground">
              {entries.length}
            </span>{" "}
            {entries.length === 1 ? "entry" : "entries"}
          </span>
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={entries}
        getRowKey={(entry) => entry.id}
        loading={loading}
        error={error}
        onRetry={fetchAudit}
        empty={{
          icon: ShieldIcon,
          title: "No audit entries",
          description:
            "Audit events will appear here as members and admins take actions.",
        }}
      />
    </PageShell>
  )
}
