import { useParams } from "react-router-dom"
import { RostersSection } from "@/routes/TestList"
import { useClass } from "@/features/class/useClass"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"

export default function ClassStudents() {
  const { id } = useParams()
  const cls = useClass(id)
  return (
    <PageShell>
      <PageHeader title="Students" description={cls?.name} />
      <RostersSection classId={id} />
    </PageShell>
  )
}
