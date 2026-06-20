import { useEffect, useState, useCallback, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { ArrowLeft, Printer, Download, FileText } from "lucide-react"
import { getTest, updateTest, listClasses } from "@/api/assessments"
import { listRosters, listStudents, generateSheets, mediaUrl, downloadAuthedBlob } from "@/api/omr"
import { useClass } from "@/features/class/useClass"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { ErrorState } from "@/components/ui/error-state"
import { Skeleton } from "@/components/ui/skeleton"

// ─── LogoPositionPicker — custom segmented control (NO native select) ─────────
function LogoPositionPicker({ value, onChange }) {
  const OPTIONS = [
    { value: "left", label: "Left" },
    { value: "center", label: "Center" },
    { value: "right", label: "Right" },
  ]
  return (
    <div
      role="group"
      aria-label="Logo position"
      className="flex overflow-hidden rounded-lg border border-border sm:max-w-sm"
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          aria-pressed={value === opt.value}
          className={[
            "min-h-[40px] flex-1 border-r border-border px-2 py-2 text-sm font-medium transition-colors last:border-r-0 sm:px-3",
            value === opt.value
              ? "bg-primary text-primary-foreground"
              : "bg-background text-foreground hover:bg-muted",
          ].join(" ")}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

// ─── Dedicated "Generate & Print" page ─────────────────────────────────────────
//
// Replaces the old GenerateSheetsDialog modal. One page that lets a teacher (1)
// edit the sheet's heading + logo (branding was previously creation-only) and
// (2) pick a roster + generate the personalised OMR sheets, then open/print or
// download them. Reached from the class page's "Generate sheets" action.

export default function GenerateSheets() {
  const { testId } = useParams()

  const [test, setTest] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Branding (seeded from the test once loaded)
  const [brandInheritOrg, setBrandInheritOrg] = useState(true)
  const [sheetHeading, setSheetHeading] = useState("")
  const [logoPosition, setLogoPosition] = useState("left")
  const [logoFile, setLogoFile] = useState(null)
  const [logoRemoved, setLogoRemoved] = useState(false)
  const [savingBrand, setSavingBrand] = useState(false)
  const logoInputRef = useRef(null)

  // Group names for human-readable roster labels (class / section).
  const ownGroup = useClass(test?.class_group)
  const parentClass = useClass(ownGroup?.parent ?? null)
  const topClassName = (ownGroup?.parent ? parentClass?.name : ownGroup?.name) ?? "Class"
  const ownGroupSectionName = ownGroup?.parent ? ownGroup?.name : null
  const rosterLabel = (r) => {
    const sec = r._section ?? ownGroupSectionName
    return sec ? `${topClassName} · ${sec}` : topClassName
  }

  // Generation
  const [rosters, setRosters] = useState([])
  const [rosterId, setRosterId] = useState("")
  // Per-student selection (default: all in the chosen roster).
  const [students, setStudents] = useState([])
  const [selectedStudentIds, setSelectedStudentIds] = useState([])
  const [studentsLoading, setStudentsLoading] = useState(false)
  const [shuffleQuestions, setShuffleQuestions] = useState(true)
  const [shuffleOptions, setShuffleOptions] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState(null)
  // batch_paper_url is an AUTHED API endpoint (not a /media/ link)
  const [paperBatchUrl, setPaperBatchUrl] = useState(null)
  const [downloadingPaper, setDownloadingPaper] = useState(false)

  const loadTest = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const t = await getTest(testId)
      setTest(t)
      setBrandInheritOrg(t.brand_inherit_org ?? true)
      setSheetHeading(t.sheet_heading ?? "")
      setLogoPosition(t.logo_position ?? "left")
      setLogoFile(null)
      setLogoRemoved(false)
      // Rosters can live on the exam's group OR (for a whole-class exam) on any
      // of its sections — gather them all, labelled by section, so you can print
      // per-section sheets from one place.
      const secD = await listClasses({ parent: t.class_group })
      const secs = secD.results ?? secD
      const groups = [
        { id: t.class_group, label: null },
        ...secs.map((s) => ({ id: s.id, label: s.name })),
      ]
      const perGroup = await Promise.all(
        groups.map(async (g) => {
          const r = await listRosters({ class_group: g.id })
          return (r.results ?? r).map((ro) => ({ ...ro, _section: g.label }))
        }),
      )
      const allRosters = perGroup.flat()
      setRosters(allRosters)
      // Pre-select the roster for the exam's OWN group (the current section's
      // students), so a section test defaults to that section's roster.
      const own = allRosters.find((ro) => String(ro.class_group) === String(t.class_group))
      if (own) setRosterId(String(own.id))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [testId])

  useEffect(() => {
    loadTest()
  }, [loadTest])

  // Load the selected roster's students for per-student selection (default: all).
  useEffect(() => {
    if (!rosterId) {
      setStudents([])
      setSelectedStudentIds([])
      return
    }
    let cancelled = false
    setStudentsLoading(true)
    listStudents(rosterId)
      .then((d) => {
        if (cancelled) return
        const list = d.results ?? d
        setStudents(list)
        setSelectedStudentIds(list.map((s) => String(s.id)))
      })
      .catch(() => {
        if (!cancelled) {
          setStudents([])
          setSelectedStudentIds([])
        }
      })
      .finally(() => {
        if (!cancelled) setStudentsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [rosterId])

  const allSelected = students.length > 0 && selectedStudentIds.length === students.length
  function toggleAllStudents() {
    setSelectedStudentIds(allSelected ? [] : students.map((s) => String(s.id)))
  }
  function toggleStudent(sid) {
    setSelectedStudentIds((ids) =>
      ids.includes(sid) ? ids.filter((x) => x !== sid) : [...ids, sid],
    )
  }

  async function handleSaveBranding() {
    setSavingBrand(true)
    try {
      let saved
      if (brandInheritOrg) {
        // Inheriting org branding → leave the test's own heading/logo fields
        // untouched; a partial PATCH that omits them preserves them (so flipping
        // inherit on then off never silently wipes a custom heading the user
        // couldn't even see while inherit was on).
        saved = await updateTest(testId, { brand_inherit_org: true })
      } else if (logoFile) {
        // New logo → multipart.
        const fd = new FormData()
        fd.append("sheet_heading", sheetHeading.trim())
        fd.append("logo", logoFile)
        fd.append("logo_position", logoPosition)
        fd.append("brand_inherit_org", "false")
        saved = await updateTest(testId, fd)
      } else {
        // No new file → JSON. Only send logo:null when explicitly cleared, so an
        // unchanged logo survives the partial PATCH.
        const payload = {
          sheet_heading: sheetHeading.trim(),
          logo_position: logoPosition,
          brand_inherit_org: false,
        }
        if (logoRemoved) payload.logo = null
        saved = await updateTest(testId, payload)
      }
      setTest(saved)
      setLogoFile(null)
      setLogoRemoved(false)
      if (logoInputRef.current) logoInputRef.current.value = ""
      toast.success("Branding saved")
    } catch (err) {
      const msg =
        err?.response?.data?.logo?.[0] ||
        err?.response?.data?.detail ||
        "Failed to save branding"
      toast.error(msg)
    } finally {
      setSavingBrand(false)
    }
  }

  async function handleGenerate() {
    if (!rosterId) {
      toast.error("Please select a roster")
      return
    }
    setGenerating(true)
    setDownloadUrl(null)
    setPaperBatchUrl(null)
    try {
      const resp = await generateSheets({
        test: testId,
        roster: rosterId,
        student_ids: selectedStudentIds,
        shuffle_questions: shuffleQuestions,
        shuffle_options: shuffleOptions,
      })
      const url = mediaUrl(resp.batch_pdf_url)
      if (!url) {
        // 2xx but no document → don't show a success with nothing to open/print.
        toast.error("Sheets were generated but no document was returned. Please try again.")
        return
      }
      setDownloadUrl(url)
      // batch_paper_url present when shuffle was on → question papers were emitted
      if (resp.batch_paper_url) setPaperBatchUrl(resp.batch_paper_url)
      toast.success(`Generated ${resp.count ?? resp.sheets?.length ?? 0} sheet(s)`)
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Failed to generate sheets"
      toast.error(detail)
    } finally {
      setGenerating(false)
    }
  }

  async function handleDownloadPapers() {
    if (!paperBatchUrl) return
    setDownloadingPaper(true)
    try {
      await downloadAuthedBlob(paperBatchUrl, "question-papers.pdf")
    } catch {
      toast.error("Failed to download question papers")
    } finally {
      setDownloadingPaper(false)
    }
  }

  if (loading) {
    return (
      <PageShell>
        <div className="space-y-2">
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-4 w-40" />
        </div>
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </PageShell>
    )
  }

  if (error || !test) {
    return (
      <PageShell>
        <ErrorState
          title="Couldn't load this test"
          description="Something went wrong while loading the test. Please try again."
          onRetry={loadTest}
        />
      </PageShell>
    )
  }

  const existingLogo = test.logo && !logoRemoved && !logoFile ? mediaUrl(test.logo) : null

  return (
    <PageShell>
      <PageHeader
        title="Generate OMR sheets"
        description={test.title}
        actions={
          <Button variant="outline" asChild className="min-h-[40px]">
            <Link to={`/classes/${test.class_group}`}>
              <ArrowLeft className="size-4" aria-hidden="true" /> Back to class
            </Link>
          </Button>
        }
      />

      {/* 1 — Sheet branding (heading + logo) */}
      <section className="space-y-4 rounded-xl border border-border p-4 sm:p-5">
        <div>
          <h2 className="text-sm font-semibold">Sheet heading &amp; logo</h2>
          <p className="text-sm text-muted-foreground">
            Printed at the top of every sheet. Save changes before generating.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Switch
            id="brand-inherit-org"
            checked={brandInheritOrg}
            onCheckedChange={setBrandInheritOrg}
          />
          <Label htmlFor="brand-inherit-org" className="cursor-pointer text-sm">
            Use organisation logo and heading
          </Label>
        </div>

        {!brandInheritOrg && (
          <div className="space-y-4 pt-1">
            <div className="space-y-1.5">
              <Label htmlFor="sheet-heading">Sheet heading</Label>
              <Input
                id="sheet-heading"
                placeholder="e.g. Springfield High School"
                value={sheetHeading}
                onChange={(e) => setSheetHeading(e.target.value)}
                className="sm:max-w-sm"
              />
            </div>

            <div role="group" aria-label="Logo" className="space-y-1.5">
              <Label>Logo</Label>
              {existingLogo && (
                <div className="mb-1 flex items-center gap-3">
                  <img
                    src={existingLogo}
                    alt="Current sheet logo"
                    className="size-12 rounded border border-border bg-surface-2 object-contain"
                  />
                  <span className="text-xs text-muted-foreground">Current logo</span>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="min-h-[40px]"
                  onClick={() => logoInputRef.current?.click()}
                >
                  {logoFile ? "Change logo" : existingLogo ? "Replace logo" : "Upload logo"}
                </Button>
                {logoFile && (
                  <span className="max-w-[180px] truncate text-sm text-muted-foreground">
                    {logoFile.name}
                  </span>
                )}
                {(logoFile || existingLogo) && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="min-h-[40px]"
                    onClick={() => {
                      setLogoFile(null)
                      setLogoRemoved(true)
                      if (logoInputRef.current) logoInputRef.current.value = ""
                    }}
                  >
                    Remove
                  </Button>
                )}
              </div>
              {/* Hidden native file input — never expose an unstyled control */}
              <input
                ref={logoInputRef}
                type="file"
                accept="image/png,image/jpeg"
                className="sr-only"
                aria-label="Upload logo image"
                onChange={(e) => {
                  const f = e.target.files?.[0] ?? null
                  // Reject oversize logos instantly instead of after a doomed upload.
                  if (f && f.size > 2 * 1024 * 1024) {
                    toast.error("Logo must be 2 MB or smaller")
                    e.target.value = ""
                    return
                  }
                  setLogoFile(f)
                  setLogoRemoved(false)
                }}
              />
              <p className="text-xs text-muted-foreground">PNG or JPEG, max 2 MB</p>
            </div>

            <div className="space-y-1.5">
              <Label>Logo position</Label>
              <LogoPositionPicker value={logoPosition} onChange={setLogoPosition} />
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={handleSaveBranding} disabled={savingBrand} className="min-h-[40px]">
            {savingBrand ? "Saving…" : "Save branding"}
          </Button>
        </div>
      </section>

      {/* 2 — Generate & print */}
      <section className="space-y-4 rounded-xl border border-border p-4 sm:p-5">
        <div>
          <h2 className="text-sm font-semibold">Generate &amp; print</h2>
          <p className="text-sm text-muted-foreground">
            Pick a roster and produce one personalised OMR sheet per student.
          </p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="roster-select">Roster</Label>
          {rosters.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              This class has no rosters yet.{" "}
              <Link
                to={`/classes/${test.class_group}`}
                className="font-medium text-primary hover:underline"
              >
                Add one in the class
              </Link>
              , then come back to generate.
            </p>
          ) : (
            <Select value={rosterId} onValueChange={setRosterId}>
              <SelectTrigger id="roster-select" className="min-h-[40px] w-full sm:max-w-sm">
                <SelectValue placeholder="Select a roster…" />
              </SelectTrigger>
              <SelectContent>
                {rosters.map((r) => (
                  <SelectItem key={r.id} value={String(r.id)}>
                    {rosterLabel(r)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {/* Per-student selection — generate for all, or pick specific students */}
        {rosterId && (
          <div className="space-y-2 sm:max-w-sm">
            <div className="flex items-center justify-between">
              <Label>Students</Label>
              {students.length > 0 && (
                <button
                  type="button"
                  onClick={toggleAllStudents}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  {allSelected ? "Clear all" : "Select all"}
                </button>
              )}
            </div>
            {studentsLoading ? (
              <Skeleton className="h-24 w-full rounded-lg" />
            ) : students.length === 0 ? (
              <p className="text-sm text-muted-foreground">This roster has no students yet.</p>
            ) : (
              <>
                <div className="max-h-56 space-y-0.5 overflow-y-auto rounded-lg border border-border p-2">
                  {students.map((s) => {
                    const sid = String(s.id)
                    return (
                      <label
                        key={sid}
                        className="flex min-h-[36px] cursor-pointer items-center gap-2 rounded-md px-2 py-1 hover:bg-muted"
                      >
                        <Checkbox
                          checked={selectedStudentIds.includes(sid)}
                          onCheckedChange={() => toggleStudent(sid)}
                        />
                        <span className="w-10 shrink-0 font-mono text-xs tabular-nums">
                          {s.roll_number}
                        </span>
                        <span className="truncate text-sm">{s.full_name || "—"}</span>
                      </label>
                    )
                  })}
                </div>
                <p className="text-xs text-muted-foreground">
                  {selectedStudentIds.length} of {students.length} selected
                </p>
              </>
            )}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:max-w-sm">
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

        <div>
          <Button
            onClick={handleGenerate}
            disabled={generating || !rosterId || selectedStudentIds.length === 0}
            className="min-h-[44px]"
          >
            {generating
              ? "Generating…"
              : selectedStudentIds.length > 0 && !allSelected
                ? `Generate ${selectedStudentIds.length} sheet${selectedStudentIds.length === 1 ? "" : "s"}`
                : "Generate sheets"}
          </Button>
        </div>

        {downloadUrl && (
          <div className="rounded-lg border border-[var(--color-success)]/40 bg-[color-mix(in_oklch,var(--color-success)_10%,transparent)] p-3 sm:p-4">
            <p className="mb-3 text-sm font-medium text-[var(--color-success)]">
              Sheets generated successfully!
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                className="min-h-[40px]"
                onClick={() => window.open(downloadUrl, "_blank", "noopener")}
              >
                <Printer className="size-4" aria-hidden="true" /> Open &amp; print
              </Button>
              <Button asChild variant="outline" className="min-h-[40px]">
                <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
                  <Download className="size-4" aria-hidden="true" /> Download sheets PDF
                </a>
              </Button>
              {paperBatchUrl && (
                <Button
                  variant="outline"
                  className="min-h-[40px]"
                  onClick={handleDownloadPapers}
                  disabled={downloadingPaper}
                >
                  <FileText className="size-4" aria-hidden="true" />{" "}
                  {downloadingPaper ? "Downloading…" : "Download question papers"}
                </Button>
              )}
            </div>
          </div>
        )}
      </section>
    </PageShell>
  )
}
