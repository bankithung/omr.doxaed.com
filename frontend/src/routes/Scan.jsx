import { useEffect, useRef, useState, useCallback } from "react"
import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { uploadScan, getBatch } from "@/api/scan"
import { listTests } from "@/api/assessments"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"

const POLL_INTERVAL_MS = 1500

export default function Scan() {
  const { testId: routeTestId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // testId from route or query param
  const [testId, setTestId] = useState(routeTestId ?? searchParams.get("test") ?? "")
  const [tests, setTests] = useState([])
  const [loadingTests, setLoadingTests] = useState(!routeTestId)

  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)

  // Poll state
  const [batch, setBatch] = useState(null) // {id, status, total, processed}
  const [done, setDone] = useState(false)
  const pollRef = useRef(null)
  const fileInputRef = useRef(null)

  // Load all tests when no testId pre-selected
  useEffect(() => {
    if (routeTestId) return
    setLoadingTests(true)
    listTests()
      .then((data) => setTests(data.results ?? data))
      .catch(() => toast.error("Failed to load tests"))
      .finally(() => setLoadingTests(false))
  }, [routeTestId])

  // Cleanup poll on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startPolling = useCallback((batchId) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const data = await getBatch(batchId)
        setBatch(data)
        if (data.status === "done" || data.processed >= data.total) {
          clearInterval(pollRef.current)
          pollRef.current = null
          setDone(true)
          toast.success(`Scan complete — ${data.processed} sheet(s) processed`)
        }
      } catch {
        clearInterval(pollRef.current)
        pollRef.current = null
        toast.error("Lost connection while polling scan progress")
      }
    }, POLL_INTERVAL_MS)
  }, [])

  function handleFileChange(e) {
    setFiles(Array.from(e.target.files))
  }

  async function handleUpload() {
    if (!testId) {
      toast.error("Please select a test first")
      return
    }
    if (files.length === 0) {
      toast.error("Please select at least one file")
      return
    }
    setUploading(true)
    setBatch(null)
    setDone(false)
    try {
      const resp = await uploadScan(testId, files)
      setBatch({ id: resp.batch_id, status: "processing", total: resp.total, processed: 0 })
      toast.success(`Scan started — ${resp.total} image(s) queued`)
      startPolling(resp.batch_id)
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        "Upload failed"
      toast.error(msg)
    } finally {
      setUploading(false)
    }
  }

  function handleReset() {
    setBatch(null)
    setDone(false)
    setFiles([])
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const pct = batch ? Math.round(((batch.processed ?? 0) / Math.max(batch.total, 1)) * 100) : 0

  return (
    <div className="mx-auto max-w-xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Scan OMR sheets</h1>

      {/* Test selector — only shown when not pre-selected via route */}
      {!routeTestId && (
        <div className="mb-6 flex flex-col gap-1.5">
          <Label>Test</Label>
          {loadingTests ? (
            <p className="text-sm text-muted-foreground">Loading tests…</p>
          ) : tests.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No tests found.{" "}
              <Link to="/classes" className="underline hover:text-foreground">
                Go to classes
              </Link>
            </p>
          ) : (
            <Select value={testId} onValueChange={setTestId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a test…" />
              </SelectTrigger>
              <SelectContent>
                {tests.map((t) => (
                  <SelectItem key={t.id} value={String(t.id)}>
                    {t.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      )}

      {/* File picker */}
      <div className="mb-6 flex flex-col gap-1.5">
        <Label>Scanned sheets (images or PDF)</Label>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || Boolean(batch)}
          >
            Choose files
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,.pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          {files.length > 0 && (
            <span className="text-sm text-muted-foreground">
              {files.length} file{files.length !== 1 ? "s" : ""} selected
            </span>
          )}
        </div>
        {files.length > 0 && (
          <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
            {files.map((f, i) => (
              <li key={i} className="truncate">
                {f.name}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Upload button */}
      {!batch && (
        <Button
          onClick={handleUpload}
          disabled={uploading || files.length === 0 || !testId}
          className="w-full"
        >
          {uploading ? "Uploading…" : "Upload & scan"}
        </Button>
      )}

      {/* Progress */}
      {batch && !done && (
        <div className="mt-6 flex flex-col gap-3">
          <p className="text-sm font-medium">
            Processing… {batch.processed ?? 0}/{batch.total} sheets
          </p>
          <Progress value={pct} className="h-3" />
          <p className="text-xs text-muted-foreground">{pct}% complete</p>
        </div>
      )}

      {/* Done summary */}
      {done && batch && (
        <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950/30">
          <p className="mb-3 font-semibold text-green-800 dark:text-green-300">
            Scan complete!
          </p>
          <p className="mb-4 text-sm text-green-700 dark:text-green-400">
            {batch.processed} of {batch.total} sheet(s) processed successfully.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm">
              <Link to={`/tests/${testId}/results`}>View results</Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to={`/tests/${testId}/review`}>Review queue</Link>
            </Button>
            <Button size="sm" variant="ghost" onClick={handleReset}>
              Scan more
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
