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
      test: Number(testId),
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

  const savedCount = questions.filter((q) => q.saved).length

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
        <div className="max-w-2xl space-y-4">
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
    </PageShell>
  )
}
