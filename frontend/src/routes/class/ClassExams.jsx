import { useParams, useNavigate } from "react-router-dom"
import { ExamsSection } from "@/routes/TestList"
import { useClass } from "@/features/class/useClass"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

export default function ClassExams() {
  const { id } = useParams()
  const navigate = useNavigate()
  const cls = useClass(id)
  return (
    <PageShell>
      <PageHeader
        title="Exams"
        description={cls?.name}
        actions={<Button onClick={() => navigate(`/classes/${id}/tests/new`)}>New exam</Button>}
      />
      <ExamsSection classId={id} />
    </PageShell>
  )
}
