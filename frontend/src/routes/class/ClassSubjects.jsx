import { useParams } from "react-router-dom"
import { SubjectsSection } from "@/routes/TestList"
import { useClass } from "@/features/class/useClass"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

export default function ClassSubjects() {
  const { id } = useParams()
  const cls = useClass(id)
  return (
    <PageShell>
      <PageHeader title="Subjects" description={cls?.name} />
      <SubjectsSection classId={id} />
    </PageShell>
  )
}
