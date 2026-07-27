/**
 * SheetCorrectorPanel
 *
 * Full-screen modal on mobile, wide Dialog on desktop.
 * Shows the warped sheet image (authenticated blob) with overlaid bubble marks,
 * plus a whole-sheet A–F toggle grid for corrections.
 * "Save & re-grade" calls POST /omr/sheets/<id>/regrade/.
 */
import { useEffect, useRef, useState, useCallback } from "react"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { getWarpedImageUrl, regradeSheet } from "@/api/scan"

function BubbleOverlay({ bubbleGeometry, detectedAnswers, imgNaturalW, imgNaturalH, imgRenderedW, imgRenderedH }) {
  if (!bubbleGeometry || !imgNaturalW || !imgNaturalH || !imgRenderedW || !imgRenderedH) return null

  const scaleX = imgRenderedW / imgNaturalW
  const scaleY = imgRenderedH / imgNaturalH

  // Build a set of answered q_pos+label pairs for quick lookup
  const markedSet = new Set()
  const flagMap = {}
  if (detectedAnswers) {
    Object.entries(detectedAnswers).forEach(([q_pos, entry]) => {
      const marked = entry?.marked ?? []
      marked.forEach((lbl) => markedSet.add(`${q_pos}:${lbl}`))
      if (entry?.flag) flagMap[`${q_pos}`] = entry.flag
    })
  }

  return (
    <svg
      className="pointer-events-none absolute inset-0"
      style={{ width: imgRenderedW, height: imgRenderedH }}
      viewBox={`0 0 ${imgRenderedW} ${imgRenderedH}`}
    >
      {bubbleGeometry.map((b, i) => {
        const cx = b.cx * scaleX
        const cy = b.cy * scaleY
        const r = Math.max(b.r * Math.min(scaleX, scaleY), 3)
        const key = `${b.q_pos}:${b.label}`
        const isMarked = markedSet.has(key)
        const flag = flagMap[String(b.q_pos)]

        let fill = "transparent"
        let stroke = "rgba(100,100,100,0.3)"
        let strokeDash = "none"
        let strokeWidth = 1

        if (isMarked) {
          if (flag === "double_mark") {
            fill = "rgba(245,158,11,0.55)"
            stroke = "rgb(217,119,6)"
            strokeWidth = 2
          } else if (flag === "faint") {
            fill = "transparent"
            stroke = "rgb(120,120,120)"
            strokeDash = "3 2"
            strokeWidth = 1.5
          } else {
            fill = "rgba(34,197,94,0.6)"
            stroke = "rgb(22,163,74)"
            strokeWidth = 2
          }
        } else if (flag === "blank") {
          stroke = "rgba(150,150,150,0.3)"
          strokeWidth = 1
        }

        return (
          <circle
            key={`${i}-${key}`}
            cx={cx}
            cy={cy}
            r={r}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={strokeDash}
          />
        )
      })}
    </svg>
  )
}

function AnswerToggleGrid({ answers, onChange, numQuestions }) {
  // answers: { [q_pos]: [labels] }
  const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"]

  // Determine number of options from the answer data keys
  // Default to 4, expand if we see more
  const maxOption = Object.values(answers).reduce((acc, labels) => {
    labels.forEach((l) => {
      const idx = OPTION_LABELS.indexOf(l)
      if (idx >= 0 && idx + 1 > acc) acc = idx + 1
    })
    return acc
  }, 4)
  const numOptions = Math.min(Math.max(maxOption, 4), 6)
  const options = OPTION_LABELS.slice(0, numOptions)

  function toggle(qPos, label) {
    const current = answers[qPos] ?? []
    const next = current.includes(label)
      ? current.filter((l) => l !== label)
      : [...current, label]
    onChange({ ...answers, [qPos]: next })
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="py-1 pr-2 text-left text-muted-foreground font-medium w-8">Q</th>
            {options.map((lbl) => (
              <th key={lbl} className="py-1 text-center text-muted-foreground font-medium w-9">
                {lbl}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: numQuestions }, (_, i) => {
            const qPos = i
            const selected = answers[qPos] ?? []
            return (
              <tr key={qPos} className="border-t border-border/50">
                <td className="py-1 pr-2 text-muted-foreground font-medium">{qPos + 1}</td>
                {options.map((lbl) => {
                  const isOn = selected.includes(lbl)
                  return (
                    <td key={lbl} className="py-0.5 text-center">
                      <button
                        type="button"
                        aria-pressed={isOn}
                        onClick={() => toggle(qPos, lbl)}
                        className={`inline-flex min-h-[32px] min-w-[32px] items-center justify-center rounded border text-xs font-semibold transition-colors ${
                          isOn
                            ? "border-indigo bg-primary text-primary-foreground"
                            : "border-input bg-transparent text-foreground hover:bg-muted"
                        }`}
                      >
                        {lbl}
                      </button>
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function SheetCorrectorPanel({ sheet, open, onClose, onRegraded }) {
  const [warpedUrl, setWarpedUrl] = useState(null)
  const [loadingImage, setLoadingImage] = useState(false)
  const [imgNaturalSize, setImgNaturalSize] = useState({ w: 0, h: 0 })
  const [imgRenderedSize, setImgRenderedSize] = useState({ w: 0, h: 0 })
  const [answers, setAnswers] = useState({})
  const [roll, setRoll] = useState("")
  const [saving, setSaving] = useState(false)
  const imgRef = useRef(null)
  const blobUrlRef = useRef(null)

  // How many questions does this sheet have?
  const numQuestions = sheet
    ? Math.max(
        Object.keys(sheet.detected?.answers ?? {}).length,
        Object.keys(sheet.answer_key ?? {}).length,
        1
      )
    : 0

  // Build initial answers from detected reads
  const buildInitialAnswers = useCallback((s) => {
    if (!s?.detected?.answers) return {}
    const init = {}
    Object.entries(s.detected.answers).forEach(([q_pos, entry]) => {
      init[Number(q_pos)] = entry?.marked ?? []
    })
    return init
  }, [])

  // When sheet changes, reset state
  useEffect(() => {
    if (!sheet || !open) return
    setAnswers(buildInitialAnswers(sheet))
    setRoll(sheet.student?.roll ?? sheet.detected?.roll ?? "")

    // Load warped image
    if (sheet.id) {
      setLoadingImage(true)
      setWarpedUrl(null)
      // Revoke previous blob URL
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
      getWarpedImageUrl(sheet.id)
        .then((url) => {
          blobUrlRef.current = url
          setWarpedUrl(url)
        })
        .catch(() => {
          toast.error("Could not load sheet image")
        })
        .finally(() => setLoadingImage(false))
    }
  }, [sheet, open, buildInitialAnswers])

  // Clean up blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [])

  // Track rendered image size for overlay scaling
  const handleImgLoad = useCallback((e) => {
    const img = e.currentTarget
    setImgNaturalSize({ w: img.naturalWidth, h: img.naturalHeight })
    const rect = img.getBoundingClientRect()
    setImgRenderedSize({ w: rect.width, h: rect.height })
  }, [])

  // Also re-measure on resize
  useEffect(() => {
    if (!imgRef.current) return
    const obs = new ResizeObserver(() => {
      if (imgRef.current) {
        const rect = imgRef.current.getBoundingClientRect()
        setImgRenderedSize({ w: rect.width, h: rect.height })
      }
    })
    obs.observe(imgRef.current)
    return () => obs.disconnect()
  }, [warpedUrl])

  async function handleSave() {
    if (!sheet?.omr_sheet_id) {
      toast.error("No sheet ID, cannot regrade")
      return
    }
    setSaving(true)
    try {
      const result = await regradeSheet(
        sheet.omr_sheet_id,
        answers,
        roll || null,
        null
      )
      toast.success("Sheet re-graded successfully")
      onRegraded(sheet.id, result)
      onClose()
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        "Failed to regrade"
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  if (!sheet) return null

  const studentName = sheet.student?.name ?? "Unknown student"
  const studentRoll = sheet.student?.roll ?? sheet.detected?.roll ?? "n/a"
  const detectedAnswers = sheet.detected?.answers ?? {}
  const bubbleGeometry = sheet.bubble_geometry ?? []

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent
 className="flex flex-col max-h-[95dvh] overflow-hidden w-full p-0"
        showCloseButton={true}
      >
        <DialogHeader className="px-4 pt-4 pb-3 border-b">
          <DialogTitle className="text-base font-semibold">
            Correct sheet, {studentName}
          </DialogTitle>
          <div className="flex flex-wrap gap-2 mt-1">
            <Badge variant="neutral">Roll: {studentRoll}</Badge>
            {sheet.status === "needs_review" && (
              <Badge variant="warning">Needs attention</Badge>
            )}
            {sheet.confidence != null && (
              <Badge variant="neutral">Confidence: {Math.round(sheet.confidence * 100)}%</Badge>
            )}
          </div>
        </DialogHeader>

        <div className="flex flex-col md:flex-row flex-1 overflow-hidden min-h-0">
          {/* Left: warped image with bubble overlay */}
          <div className="flex-1 overflow-auto bg-muted/30 flex items-start justify-center p-3 min-w-0">
            {loadingImage ? (
              <Skeleton className="w-full aspect-[3/4] max-w-sm" />
            ) : warpedUrl ? (
              <div className="relative inline-block">
                <img
                  ref={imgRef}
                  src={warpedUrl}
                  alt="Scanned OMR sheet"
                  className="max-w-full max-h-[50dvh] md:max-h-[70dvh] object-contain rounded border border-border"
                  onLoad={handleImgLoad}
                  draggable={false}
                />
                {imgRenderedSize.w > 0 && imgNaturalSize.w > 0 && (
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ width: imgRenderedSize.w, height: imgRenderedSize.h }}
                  >
                    <BubbleOverlay
                      bubbleGeometry={bubbleGeometry}
                      detectedAnswers={detectedAnswers}
                      imgNaturalW={imgNaturalSize.w}
                      imgNaturalH={imgNaturalSize.h}
                      imgRenderedW={imgRenderedSize.w}
                      imgRenderedH={imgRenderedSize.h}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground p-6 text-center">
                No sheet image available
              </div>
            )}
          </div>

          {/* Right: correction controls */}
          <div className="w-full md:w-72 shrink-0 flex flex-col overflow-hidden border-t md:border-t-0 md:border-l">
            <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-4">
              {/* Roll correction */}
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="correct-roll" className="text-xs font-medium">
                  Student roll (correct if wrong)
                </Label>
                <Input
                  id="correct-roll"
                  value={roll}
                  onChange={(e) => setRoll(e.target.value)}
                  placeholder="Roll number"
                  className="h-9 text-sm"
                />
              </div>

              {/* Answer toggle grid */}
              <div>
                <p className="text-xs font-medium mb-2">Mark correct bubbles per question</p>
                <AnswerToggleGrid
                  answers={answers}
                  onChange={setAnswers}
                  numQuestions={numQuestions}
                />
              </div>

              {/* Legend */}
              <div className="text-xs text-muted-foreground space-y-1 border-t pt-2">
                <p className="font-medium mb-1">Overlay key</p>
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-full bg-green-500/70 border border-green-600" />
                  <span>Marked (clean)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-full bg-amber-400/60 border-2 border-amber-500" />
                  <span>Double mark</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-full border border-dashed border-muted-foreground" />
                  <span>Faint bubble</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="px-4 py-3 border-t bg-muted/30 flex-row justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save & re-grade"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
