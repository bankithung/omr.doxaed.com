import { useState } from "react"
import { Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// Inline field error paragraph (shared by all auth pages).
export function FieldError({ id, children }) {
  if (!children) return null
  return (
    <p id={id} className="text-sm text-destructive">
      {children}
    </p>
  )
}

// Top-of-form destructive banner for 401 / whole-form errors.
export function FormBanner({ children }) {
  if (!children) return null
  return (
    <div
      role="alert"
      className="rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive"
    >
      {children}
    </div>
  )
}

// Labelled text input with inline error wiring (aria-invalid + describedby).
// `labelRight` renders an optional accessory (e.g. a link) on the label row,
// right-aligned — the Supabase "Forgot password?" pattern.
export function TextField({ id, label, labelRight, error, className, ...props }) {
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        {labelRight}
      </div>
      <Input
        id={id}
        className={cn("h-11", className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        {...props}
      />
      <FieldError id={errorId}>{error}</FieldError>
    </div>
  )
}

// Password input with an Eye/EyeOff visibility toggle. `labelRight` renders an
// optional accessory (e.g. a "Forgot password?" link) right-aligned on the label
// row — the Supabase auth pattern.
export function PasswordField({ id, label, labelRight, error, value, onChange, ...props }) {
  const [show, setShow] = useState(false)
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        {labelRight}
      </div>
      <div className="relative">
        <Input
          id={id}
          type={show ? "text" : "password"}
          value={value}
          onChange={onChange}
          className="h-11 pr-10"
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          {...props}
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          aria-label={show ? "Hide password" : "Show password"}
          aria-pressed={show}
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-lg text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {show ? (
            <EyeOff className="size-4" aria-hidden="true" />
          ) : (
            <Eye className="size-4" aria-hidden="true" />
          )}
        </button>
      </div>
      <FieldError id={errorId}>{error}</FieldError>
    </div>
  )
}

// Heuristic password strength: 0–4. Mirrors common signup meters; the backend
// remains the source of truth for acceptance (Django validators).
export function scorePassword(pw) {
  if (!pw) return 0
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++
  if (/\d/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  return Math.min(score, 4)
}

const STRENGTH = [
  { label: "Too weak", color: "var(--color-error)" },
  { label: "Weak", color: "var(--color-error)" },
  { label: "Fair", color: "var(--color-warning)" },
  { label: "Good", color: "var(--color-info)" },
  { label: "Strong", color: "var(--color-success)" },
]

// Flat 4-segment password-strength meter (uses status tokens).
export function PasswordStrength({ password }) {
  if (!password) return null
  const score = scorePassword(password)
  const { label, color } = STRENGTH[score]
  return (
    <div className="space-y-1.5" aria-live="polite">
      <div className="flex gap-1.5" aria-hidden="true">
        {[0, 1, 2, 3].map((i) => (
          <span
            key={i}
            className="h-1.5 flex-1 rounded-full bg-border transition-colors"
            style={i < score ? { backgroundColor: color } : undefined}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Password strength: <span style={{ color }}>{label}</span>
      </p>
    </div>
  )
}
