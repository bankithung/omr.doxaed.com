import { useEffect, useState, useCallback } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { ShieldIcon } from "lucide-react"
import { useOrg } from "@/org/OrgContext"
import { getAudit } from "@/api/orgs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/list-skeletons"

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

export default function OrgAudit() {
  const { id: orgId } = useParams()
  const { orgs } = useOrg()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const org = orgs.find((o) => String(o.id) === String(orgId))

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
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2 text-sm text-muted-foreground">
            <Link
              to={`/organizations/${orgId}/members`}
              className="hover:text-foreground hover:underline"
            >
              {org?.name ?? "Organization"}
            </Link>
            <span>/</span>
            <span>Audit log</span>
          </div>
          <h1 className="text-2xl font-bold">Audit Log</h1>
        </div>
      </div>

      {loading ? (
        <TableSkeleton rows={6} />
      ) : error ? (
        <ErrorState
          title="Couldn't load audit log"
          description="Something went wrong while loading the audit log."
          onRetry={fetchAudit}
        />
      ) : entries.length === 0 ? (
        <EmptyState
          icon={ShieldIcon}
          title="No audit entries"
          description="Audit events will appear here as members and admins take actions."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>When</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="text-sm">
                    {entry.actor_email ?? <span className="italic text-muted-foreground">system</span>}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{entry.action}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {entry.target_type
                      ? `${entry.target_type}${entry.target_id != null ? ` #${entry.target_id}` : ""}`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(entry.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
