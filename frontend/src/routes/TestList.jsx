import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { toast } from "sonner"
import { getClass, listTests, retest } from "@/api/assessments"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { EmptyState } from "@/components/ui/empty-state"

const STATUS_LABELS = {
  draft: "Draft",
  ready: "Ready",
  closed: "Closed",
}

const STATUS_CLASSES = {
  draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  ready: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  closed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
}

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STATUS_CLASSES[status] ?? STATUS_CLASSES.draft
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

export default function TestList() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [classGroup, setClassGroup] = useState(null)
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [retestingId, setRetestingId] = useState(null)

  const fetchData = useCallback(async () => {
    try {
      const [cls, testsData] = await Promise.all([getClass(id), listTests(id)])
      setClassGroup(cls)
      setTests(testsData.results ?? testsData)
    } catch {
      toast.error("Failed to load class data")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  async function handleRetest(testId) {
    setRetestingId(testId)
    try {
      const newTest = await retest(testId)
      toast.success(`Retest created: attempt #${newTest.attempt_number}`)
      fetchData()
    } catch {
      toast.error("Failed to create retest")
    } finally {
      setRetestingId(null)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/classes" className="hover:text-foreground hover:underline">
          Classes
        </Link>
        <span>/</span>
        <span>{classGroup?.name ?? "Class"}</span>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{classGroup?.name ?? "Class"}</h1>
          {classGroup?.description && (
            <p className="text-sm text-muted-foreground">{classGroup.description}</p>
          )}
        </div>
        <Button onClick={() => navigate(`/classes/${id}/tests/new`)}>
          Create test
        </Button>
      </div>

      {tests.length === 0 ? (
        <EmptyState
          title="No tests yet"
          description="Create the first test for this class."
          action={
            <Button onClick={() => navigate(`/classes/${id}/tests/new`)}>
              Create test
            </Button>
          }
        />
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Attempt</TableHead>
                <TableHead className="w-28 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tests.map((test) => (
                <TableRow key={test.id}>
                  <TableCell className="font-medium">{test.title}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {test.subject || <span className="italic">—</span>}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={test.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    #{test.attempt_number}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={retestingId === test.id}
                      onClick={() => handleRetest(test.id)}
                    >
                      {retestingId === test.id ? "Creating…" : "Retest"}
                    </Button>
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
