import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { createTest, createQuestion, updateTest } from "@/api/assessments"
import { Stepper } from "@/components/ui/stepper"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"

// ─── Helpers ──────────────────────────────────────────────────────────────────
const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"]

function makeBlankOption(idx) {
  return { label: OPTION_LABELS[idx], text: "", is_correct: false }
}

function makeBlankQuestion() {
  return { text: "", options: [makeBlankOption(0), makeBlankOption(1)], saved: false }
}

// ─── QuestionEditor ───────────────────────────────────────────────────────────
// Manages local edit state for a single question card.
function QuestionEditor({ question, index, multipleCorrect, onChange, onRemove, onSave, saving }) {
  function setQuestionText(text) {
    onChange({ ...question, text, saved: false })
  }

  function setOptionText(optIdx, text) {
    const options = question.options.map((o, i) => (i === optIdx ? { ...o, text } : o))
    onChange({ ...question, options, saved: false })
  }

  function setCorrect(optIdx, value) {
    const options = multipleCorrect
      ? // checkbox: toggle independently
        question.options.map((o, i) => (i === optIdx ? { ...o, is_correct: value } : o))
      : // radio: exactly one correct
        question.options.map((o, i) => ({ ...o, is_correct: i === optIdx }))
    onChange({ ...question, options, saved: false })
  }

  function handleRadioChange(label) {
    const options = question.options.map((o) => ({ ...o, is_correct: o.label === label }))
    onChange({ ...question, options, saved: false })
  }

  function addOption() {
    if (question.options.length >= 6) return
    const newIdx = question.options.length
    onChange({
      ...question,
      options: [...question.options, makeBlankOption(newIdx)],
      saved: false,
    })
  }

  function removeOption(optIdx) {
    if (question.options.length <= 2) return
    const options = question.options
      .filter((_, i) => i !== optIdx)
      .map((o, i) => ({ ...o, label: OPTION_LABELS[i] }))
    onChange({ ...question, options, saved: false })
  }

  const radioValue = question.options.find((o) => o.is_correct)?.label ?? ""

  const canSave =
    question.text.trim() !== "" &&
    question.options.every((o) => o.text.trim() !== "") &&
    question.options.some((o) => o.is_correct)

  return (
    <div className="rounded-xl border p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-muted-foreground">
          Question {index + 1}
        </span>
        <Button variant="ghost" size="sm" type="button" onClick={onRemove}>
          Remove
        </Button>
      </div>

      {/* Question text */}
      <div className="space-y-1.5">
        <Label htmlFor={`q-text-${index}`}>Question text</Label>
        <Textarea
          id={`q-text-${index}`}
          placeholder="Enter question text…"
          value={question.text}
          onChange={(e) => setQuestionText(e.target.value)}
          rows={2}
        />
      </div>

      {/* Options */}
      <div className="space-y-2">
        <Label>
          Options{" "}
          <span className="text-xs text-muted-foreground font-normal">
            ({multipleCorrect ? "tick all correct answers" : "select one correct answer"})
          </span>
        </Label>

        {multipleCorrect ? (
          <div className="space-y-2">
            {question.options.map((opt, optIdx) => (
              <div key={opt.label} className="flex items-center gap-2">
                <Checkbox
                  id={`q${index}-opt${optIdx}-chk`}
                  checked={opt.is_correct}
                  onCheckedChange={(checked) => setCorrect(optIdx, !!checked)}
                />
                <span className="w-5 shrink-0 text-sm font-medium text-muted-foreground">
                  {opt.label}
                </span>
                <Input
                  placeholder={`Option ${opt.label}`}
                  value={opt.text}
                  onChange={(e) => setOptionText(optIdx, e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="ghost"
                  size="icon-sm"
                  type="button"
                  disabled={question.options.length <= 2}
                  onClick={() => removeOption(optIdx)}
                  aria-label={`Remove option ${opt.label}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <RadioGroup value={radioValue} onValueChange={handleRadioChange} className="space-y-2">
            {question.options.map((opt, optIdx) => (
              <div key={opt.label} className="flex items-center gap-2">
                <RadioGroupItem
                  id={`q${index}-opt${optIdx}-radio`}
                  value={opt.label}
                />
                <span className="w-5 shrink-0 text-sm font-medium text-muted-foreground">
                  {opt.label}
                </span>
                <Input
                  placeholder={`Option ${opt.label}`}
                  value={opt.text}
                  onChange={(e) => setOptionText(optIdx, e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="ghost"
                  size="icon-sm"
                  type="button"
                  disabled={question.options.length <= 2}
                  onClick={() => removeOption(optIdx)}
                  aria-label={`Remove option ${opt.label}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </RadioGroup>
        )}

        {question.options.length < 6 && (
          <Button variant="outline" size="sm" type="button" onClick={addOption}>
            + Add option
          </Button>
        )}
      </div>

      {/* Save */}
      <div className="flex items-center gap-3 pt-1">
        <Button
          type="button"
          size="sm"
          disabled={!canSave || saving || question.saved}
          onClick={onSave}
        >
          {saving ? "Saving…" : question.saved ? "Saved" : "Save question"}
        </Button>
        {question.saved && (
          <span className="text-xs text-green-600 dark:text-green-400">Saved</span>
        )}
      </div>
    </div>
  )
}

// ─── Step 1 – Details ─────────────────────────────────────────────────────────
function StepDetails({ classId, onNext }) {
  const [title, setTitle] = useState("")
  const [subject, setSubject] = useState("")
  const [mode, setMode] = useState("standard")
  const [marksPerCorrect, setMarksPerCorrect] = useState("1")
  const [negativeMarks, setNegativeMarks] = useState("0")
  const [partialMarking, setPartialMarking] = useState(false)
  const [multipleCorrectAllowed, setMultipleCorrectAllowed] = useState(false)
  const [saving, setSaving] = useState(false)

  async function handleNext(e) {
    e.preventDefault()
    if (!title.trim()) {
      toast.error("Title is required")
      return
    }
    setSaving(true)
    try {
      const payload = {
        class_group: classId,
        title: title.trim(),
        ...(subject.trim() && { subject: subject.trim() }),
        mode,
        marking_scheme: {
          marks_per_correct: parseFloat(marksPerCorrect) || 0,
          negative_marks_per_wrong: parseFloat(negativeMarks) || 0,
          partial_marking: partialMarking,
          multiple_correct_allowed: multipleCorrectAllowed,
        },
      }
      const test = await createTest(payload)
      onNext(test.id, multipleCorrectAllowed)
    } catch (err) {
      const detail =
        err?.response?.data?.title?.[0] ||
        err?.response?.data?.class_group?.[0] ||
        err?.response?.data?.detail ||
        "Failed to create test"
      toast.error(detail)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleNext} className="space-y-6 max-w-lg">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="test-title">Title</Label>
          <Input
            id="test-title"
            placeholder="e.g. Mid-term Exam"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="test-subject">Subject</Label>
          <Input
            id="test-subject"
            placeholder="e.g. Mathematics"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </div>
      </div>

      {/* Mode picker card */}
      <div className="rounded-xl border p-4 space-y-3">
        <p className="text-sm font-medium">Test mode</p>
        <RadioGroup value={mode} onValueChange={setMode} className="space-y-3">
          <div className="flex items-start gap-3">
            <RadioGroupItem id="mode-standard" value="standard" className="mt-0.5" />
            <div>
              <Label htmlFor="mode-standard" className="cursor-pointer font-medium">
                Standard
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Students bubble their own roll number.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <RadioGroupItem id="mode-roster" value="roster_prebubbled" className="mt-0.5" />
            <div>
              <Label htmlFor="mode-roster" className="cursor-pointer font-medium">
                Roster — pre-bubbled roll numbers
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Each student's roll number is auto-printed (pre-filled) on their sheet, so scanning
                auto-identifies the student. You'll pick the roster when you generate sheets.
              </p>
            </div>
          </div>
        </RadioGroup>
      </div>

      {/* Marking scheme card */}
      <div className="rounded-xl border p-4 space-y-4">
        <p className="text-sm font-medium">Marking scheme</p>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="marks-correct">Marks per correct</Label>
            <Input
              id="marks-correct"
              type="number"
              min="0"
              step="0.5"
              value={marksPerCorrect}
              onChange={(e) => setMarksPerCorrect(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="marks-negative">Negative marks per wrong</Label>
            <Input
              id="marks-negative"
              type="number"
              min="0"
              step="0.5"
              value={negativeMarks}
              onChange={(e) => setNegativeMarks(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Switch
            id="partial-marking"
            checked={partialMarking}
            onCheckedChange={setPartialMarking}
          />
          <Label htmlFor="partial-marking" className="cursor-pointer">
            Partial marking
          </Label>
        </div>

        <div className="flex items-center gap-3">
          <Switch
            id="multiple-correct"
            checked={multipleCorrectAllowed}
            onCheckedChange={setMultipleCorrectAllowed}
          />
          <Label htmlFor="multiple-correct" className="cursor-pointer">
            Multiple correct answers allowed
          </Label>
        </div>
      </div>

      <Button type="submit" disabled={saving || !title.trim()}>
        {saving ? "Creating test…" : "Next: Add questions"}
      </Button>
    </form>
  )
}

// ─── Step 2 – Questions ───────────────────────────────────────────────────────
function StepQuestions({ testId, multipleCorrect, initialQuestions, onBack, onNext }) {
  const [questions, setQuestions] = useState(initialQuestions)
  const [savingIdx, setSavingIdx] = useState(null)

  function addQuestion() {
    setQuestions((qs) => [...qs, makeBlankQuestion()])
  }

  function updateQuestion(idx, updated) {
    setQuestions((qs) => qs.map((q, i) => (i === idx ? updated : q)))
  }

  function removeQuestion(idx) {
    if (questions.length === 1) {
      // Reset rather than leaving empty list
      setQuestions([makeBlankQuestion()])
      return
    }
    setQuestions((qs) => qs.filter((_, i) => i !== idx))
  }

  async function saveQuestion(idx) {
    const q = questions[idx]
    setSavingIdx(idx)
    try {
      await createQuestion({
        test: testId,
        order_index: idx,
        text: q.text.trim(),
        options: q.options.map((o) => ({
          label: o.label,
          text: o.text.trim(),
          is_correct: o.is_correct,
        })),
      })
      setQuestions((qs) =>
        qs.map((question, i) => (i === idx ? { ...question, saved: true } : question))
      )
      toast.success(`Question ${idx + 1} saved`)
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.text?.[0] ||
        "Failed to save question"
      toast.error(msg)
    } finally {
      setSavingIdx(null)
    }
  }

  const savedCount = questions.filter((q) => q.saved).length

  function handleNext() {
    if (savedCount === 0) {
      toast.error("Save at least one question before continuing")
      return
    }
    onNext(questions)
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {savedCount} / {questions.length} question{questions.length !== 1 ? "s" : ""} saved
        </p>
        <Button variant="outline" size="sm" type="button" onClick={addQuestion}>
          + Add question
        </Button>
      </div>

      <div className="space-y-4">
        {questions.map((q, idx) => (
          <QuestionEditor
            key={idx}
            question={q}
            index={idx}
            multipleCorrect={multipleCorrect}
            onChange={(updated) => updateQuestion(idx, updated)}
            onRemove={() => removeQuestion(idx)}
            onSave={() => saveQuestion(idx)}
            saving={savingIdx === idx}
          />
        ))}
      </div>

      <div className="flex gap-3 pt-2">
        <Button variant="outline" type="button" onClick={onBack}>
          Back
        </Button>
        <Button type="button" onClick={handleNext}>
          Next: Review
        </Button>
      </div>
    </div>
  )
}

// ─── Step 3 – Review ──────────────────────────────────────────────────────────
function StepReview({ testId, classId, questions, onBack }) {
  const navigate = useNavigate()
  const [finishing, setFinishing] = useState(false)

  const savedQuestions = questions.filter((q) => q.saved)

  async function handleFinish() {
    setFinishing(true)
    try {
      await updateTest(testId, { status: "ready" })
      toast.success("Test marked as ready!")
      navigate(`/classes/${classId}`)
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? "Failed to finalise test")
      setFinishing(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <p className="text-sm text-muted-foreground">
        {savedQuestions.length} question{savedQuestions.length !== 1 ? "s" : ""} will be included.
      </p>

      {savedQuestions.length === 0 ? (
        <p className="text-sm text-destructive">
          No questions saved. Go back and save at least one question.
        </p>
      ) : (
        <ol className="space-y-3">
          {savedQuestions.map((q, displayIdx) => {
            const correctLabels = q.options
              .filter((o) => o.is_correct)
              .map((o) => o.label)
              .join(", ")
            return (
              <li key={displayIdx} className="rounded-xl border p-4 space-y-2">
                <p className="text-sm font-medium">
                  {displayIdx + 1}. {q.text}
                </p>
                <ul className="space-y-0.5 pl-4">
                  {q.options.map((o) => (
                    <li
                      key={o.label}
                      className={`text-sm ${
                        o.is_correct
                          ? "font-medium text-green-700 dark:text-green-400"
                          : "text-muted-foreground"
                      }`}
                    >
                      {o.label}. {o.text}
                      {o.is_correct && " ✓"}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-muted-foreground">Correct: {correctLabels}</p>
              </li>
            )
          })}
        </ol>
      )}

      <div className="flex gap-3">
        <Button variant="outline" type="button" onClick={onBack}>
          Back
        </Button>
        <Button
          type="button"
          disabled={finishing || savedQuestions.length === 0}
          onClick={handleFinish}
        >
          {finishing ? "Finishing…" : "Finish & mark ready"}
        </Button>
      </div>
    </div>
  )
}

// ─── TestWizard ───────────────────────────────────────────────────────────────
const WIZARD_STEPS = ["Details", "Questions", "Review"]

export default function TestWizard() {
  const { classId } = useParams()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [testId, setTestId] = useState(null)
  const [multipleCorrect, setMultipleCorrect] = useState(false)
  // questions state is lifted here so Back from Review preserves work
  const [questions, setQuestions] = useState([makeBlankQuestion()])

  function handleDetailsNext(id, multi) {
    setTestId(id)
    setMultipleCorrect(multi)
    setStep(1)
  }

  function handleQuestionsNext(qs) {
    setQuestions(qs)
    setStep(2)
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-8">
      {/* Page header */}
      <div>
        <button
          type="button"
          className="text-sm text-muted-foreground hover:text-foreground"
          onClick={() => navigate(`/classes/${classId}`)}
        >
          ← Back to class
        </button>
        <h1 className="mt-2 text-2xl font-bold">Create test</h1>
      </div>

      {/* Step indicator */}
      <Stepper steps={WIZARD_STEPS} current={step} />

      {/* Step panels */}
      {step === 0 && (
        <StepDetails classId={classId} onNext={handleDetailsNext} />
      )}

      {step === 1 && (
        <StepQuestions
          testId={testId}
          multipleCorrect={multipleCorrect}
          initialQuestions={questions}
          onBack={() => setStep(0)}
          onNext={handleQuestionsNext}
        />
      )}

      {step === 2 && (
        <StepReview
          testId={testId}
          classId={classId}
          questions={questions}
          onBack={() => setStep(1)}
        />
      )}
    </div>
  )
}
