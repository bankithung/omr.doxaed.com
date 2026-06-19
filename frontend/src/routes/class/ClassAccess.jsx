import { useParams, Navigate } from "react-router-dom"
import { AccessSection } from "@/routes/TestList"
import { useClass } from "@/features/class/useClass"
import { useOrg } from "@/org/OrgContext"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

export default function ClassAccess() {
  const { id } = useParams()
  const cls = useClass(id)
  const { activeOrg } = useOrg() ?? {}
  // Admin-only; a non-admin who deep-links here is bounced to the class overview.
  if (activeOrg && activeOrg.role !== "admin") {
    return <Navigate to={`/classes/${id}`} replace />
  }
  return (
    <PageShell>
      <PageHeader title="Teacher access" description={cls?.name} />
      <AccessSection classId={id} />
    </PageShell>
  )
}
