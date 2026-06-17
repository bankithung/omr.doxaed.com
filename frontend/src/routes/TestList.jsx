import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { toast } from "sonner"
import { getClass, listTests, retest } from "@/api/assessments"
import { listRosters, generateSheets, mediaUrl } from "@/api/omr"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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

function GenerateSheetsDialog({ test, open, onOpenChange }) {
  const [rosters, setRosters] = useState([])
  const [rosterId, setRosterId] = useState("")
  const [shuffleQuestions, setShuffleQuestions] = useState(true)
  const [shuffleOptions, setShuffleOptions] = useState(true)
  const [loading, setLoading] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState(null)

  useEffect(() => {
    if (!open) return
    setDownloadUrl(null)
    setRosterId("")
    listRosters()
      .then((data) => setRosters(data.results ?? data))
      .catch(() => toast.error("Failed to load rosters"))
  }, [open])

  async function handleGenerate() {
    if (!rosterId) {
      toast.error("Please select a roster")
      return
    }
    setLoading(true)
    setDownloadUrl(null)
    try {
      const resp = await generateSheets({
        test: test.id,
        roster: Number(rosterId),
        shuffle_questions: shuffleQuestions,
        shuffle_options: shuffleOptions,
      })
      const url = mediaUrl(resp.batch_pdf_url)
      setDownloadUrl(url)
      toast.success(`Generated ${resp.count ?? resp.sheets?.length ?? ""} sheet(s)`)
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to generate sheets"
      toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Generate OMR sheets</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Test: <span className="font-medium text-foreground">{test.title}</span>
        </p>

        <div className="flex flex-col gap-4">
          {/* Roster picker */}
          <div className="flex flex-col gap-1.5">
            <Label>Roster</Label>
            {rosters.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No rosters found.{" "}
                <Link to="/rosters" className="underline hover:text-foreground">
                  Create one first.
                </Link>
              </p>
            ) : (
              <Select value={rosterId} onValueChange={setRosterId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a roster…" />
                </SelectTrigger>
                <SelectContent>
                  {rosters.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Shuffle toggles */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Label htmlFor="shuffle-questions" className="cursor-pointer">
                Shuffle questions
              </Label>
              <Switch
                id="shuffle-questions"
                checked={shuffleQuestions}
                onCheckedChange={setShuffleQuestions}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="shuffle-options" className="cursor-pointer">
                Shuffle options
              </Label>
              <Switch
                id="shuffle-options"
                checked={shuffleOptions}
                onCheckedChange={setShuffleOptions}
              />
            </div>
          </div>

          {/* Download link after success */}
          {downloadUrl && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-950/30">
              <p className="mb-2 text-sm font-medium text-green-800 dark:text-green-300">
                Sheets generated successfully!
              </p>
              <Button asChild size="sm" variant="outline">
                <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
                  Download sheets PDF
                </a>
              </Button>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={handleGenerate}
            disabled={loading || !rosterId}
          >
            {loading ? "Generating…" : "Generate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function TestList() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [classGroup, setClassGroup] = useState(null)
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [retestingId, setRetestingId] = useState(null)
  const [generateTest, setGenerateTest] = useState(null)

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
                <TableHead className="w-72 text-right">Actions</TableHead>
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
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setGenerateTest(test)}
                      >
                        Generate sheets
                      </Button>
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/tests/${test.id}/scan`}>Scan</Link>
                      </Button>
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/tests/${test.id}/results`}>Results</Link>
                      </Button>
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/tests/${test.id}/review`}>Review</Link>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={retestingId === test.id}
                        onClick={() => handleRetest(test.id)}
                      >
                        {retestingId === test.id ? "Creating…" : "Retest"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Generate sheets dialog */}
      {generateTest && (
        <GenerateSheetsDialog
          test={generateTest}
          open={Boolean(generateTest)}
          onOpenChange={(v) => { if (!v) setGenerateTest(null) }}
        />
      )}
    </div>
  )
}
