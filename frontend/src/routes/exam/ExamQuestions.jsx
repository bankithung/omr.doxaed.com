import { useEffect, useState, useCallback } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { Plus } from "lucide-react"
import {
  listQuestions,
  createQuestion,
  updateQuestion,
  deleteQuestion,
} from "@/api/assessments"
import { useTest } from "@/features/test/useTest"
import { QuestionEditor, makeBlankQuestion } from "@/features/test/QuestionEditor"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"

// API question → the editor's local shape. `saved: true` marks it as persisted.
function apiToEditor(q) {
  return {
    id: q.id,
    text: q.text ?? "",
    options: (q.options ?? []).map((o) => ({
      label: o.label,
      text: o.text ?? "",
      is_correct: o.is_correct,
    })),
    saved: true,
  }
}

export default function ExamQuestions() {
  const { testId } = useParams()
  const test = useTest(testId)
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [savingIdx, setSavingIdx] = useState(null)
  const [savingAll, setSavingAll] = useState(false)
  const multipleCorrect = test?.marking_scheme?.multiple_correct_allowed ?? false

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await listQuestions(testId)
      const rows = (d.results ?? d).slice().sort((a, b) => a.order_index - b.order_index)
      setQuestions(rows.length ? rows.map(apiToEditor) : [makeBlankQuestion()])
    } catch {
      toast.error("Failed to load questions")
      setQuestions([makeBlankQuestion()])
    } finally {
      setLoading(false)
    }
  }, [testId])

  useEffect(() => {
    load()
  }, [load])

  function updateQ(idx, updated) {
    setQuestions((qs) => qs.map((q, i) => (i === idx ? updated : q)))
  }

  function addQ() {
    setQuestions((qs) => [...qs, makeBlankQuestion()])
  }

  async function removeQ(idx) {
    const q = questions[idx]
    if (q.id) {
      try {
        await deleteQuestion(q.id)
        toast.success("Question removed")
      } catch {
        toast.error("Failed to remove question")
        return
      }
    }
    setQuestions((qs) => {
      const next = qs.filter((_, i) => i !== idx)
      return next.length ? next : [makeBlankQuestion()]
    })
  }

  async function saveQ(idx) {
    const q = questions[idx]
    setSavingIdx(idx)
    const payload = {
      test: testId,
      order_index: idx,
      text: q.text.trim(),
      options: q.options.map((o) => ({
        label: o.label,
        text: o.text.trim(),
        is_correct: o.is_correct,
      })),
    }
    try {
      const saved = q.id ? await updateQuestion(q.id, payload) : await createQuestion(payload)
      setQuestions((qs) =>
        qs.map((question, i) =>
          i === idx ? { ...question, id: saved.id, saved: true } : question,
        ),
      )
      toast.success(`Question ${idx + 1} saved`)
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || err?.response?.data?.text?.[0] || "Failed to save question",
      )
    } finally {
      setSavingIdx(null)
    }
  }

  // Save every question in one go (sequentially, so a failure mid-way still
  // persists the earlier ones with ids — re-running won't duplicate them).
  async function saveAll() {
    setSavingAll(true)
    let done = 0
    try {
      for (let idx = 0; idx < questions.length; idx++) {
        const q = questions[idx]
        if (q.saved) {
          done++
          continue
        }
        const payload = {
          test: testId,
          order_index: idx,
          text: q.text.trim(),
          options: q.options.map((o) => ({
            label: o.label,
            text: o.text.trim(),
            is_correct: o.is_correct,
          })),
        }
        const saved = q.id ? await updateQuestion(q.id, payload) : await createQuestion(payload)
        setQuestions((qs) =>
          qs.map((question, i) => (i === idx ? { ...question, id: saved.id, saved: true } : question)),
        )
        done++
      }
      toast.success("All questions saved")
    } catch (err) {
      toast.error(
        `Saved ${done} of ${questions.length}, ` +
          (err?.response?.data?.text?.[0] || err?.response?.data?.detail || "check the highlighted question"),
      )
    } finally {
      setSavingAll(false)
    }
  }

  const savedCount = questions.filter((q) => q.saved).length
  const unsavedCount = questions.length - savedCount

  return (
    <PageShell>
      <PageHeader
        title="Questions"
        description={test?.title}
        actions={
          <Button variant="outline" onClick={addQ}>
            <Plus className="size-4" aria-hidden="true" /> Add question
          </Button>
        }
      />

      {loading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
 <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {savedCount} / {questions.length} question{questions.length === 1 ? "" : "s"} saved
            {multipleCorrect ? " · multiple correct answers" : ""}
          </p>
          {questions.map((q, idx) => (
            <QuestionEditor
              key={q.id ?? `new-${idx}`}
              question={q}
              index={idx}
              multipleCorrect={multipleCorrect}
              onChange={(u) => updateQ(idx, u)}
              onRemove={() => removeQ(idx)}
              onSave={() => saveQ(idx)}
              saving={savingIdx === idx}
            />
          ))}
          <Button variant="outline" onClick={addQ} className="w-full">
            <Plus className="size-4" aria-hidden="true" /> Add question
          </Button>
        </div>
      )}

      {/* Sticky save bar — saves every question at once; stays pinned at the
          bottom while you scroll so you never have to save each one. */}
      {!loading && (
        <div className="sticky bottom-0 z-20 -mx-4 border-t border-border bg-background/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6">
 <div className="mx-auto flex items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              {unsavedCount === 0
                ? "All questions saved"
                : `${unsavedCount} unsaved question${unsavedCount === 1 ? "" : "s"}`}
            </span>
            <Button onClick={saveAll} disabled={savingAll || unsavedCount === 0} className="min-h-[44px]">
              {savingAll ? "Saving…" : "Save all"}
            </Button>
          </div>
        </div>
      )}
    </PageShell>
  )
}
