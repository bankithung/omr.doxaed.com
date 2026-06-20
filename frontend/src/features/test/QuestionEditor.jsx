import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"

// Shared question-editing primitives — used by the create wizard (TestWizard)
// and the post-creation editor (ExamQuestions) so both stay byte-identical.

export const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"]

export function makeBlankOption(idx) {
  return { label: OPTION_LABELS[idx], text: "", is_correct: false }
}

export function makeBlankQuestion() {
  return { text: "", options: [makeBlankOption(0), makeBlankOption(1)], saved: false }
}

// Manages local edit state for a single question card.
export function QuestionEditor({ question, index, multipleCorrect, onChange, onRemove, onSave, saving }) {
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
                  size="icon"
                  type="button"
                  className="size-10 shrink-0"
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
                  size="icon"
                  type="button"
                  className="size-10 shrink-0"
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
