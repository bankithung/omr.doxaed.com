import { useState } from "react"
import { Link } from "react-router-dom"
import { CheckCircle2, Loader2 } from "lucide-react"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import AuthLayout from "@/components/auth/AuthLayout"
import { TextField } from "@/components/auth/fields"

export default function ForgotPassword() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.passwordReset(email)
    } catch {
      // swallow errors — no enumeration
    } finally {
      setLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <AuthLayout
      title="Reset password"
      subtitle="Enter your email and we will send a reset link."
    >
      {submitted ? (
        <div className="space-y-4">
          <div className="flex gap-3 rounded-lg border border-border bg-muted/50 px-4 py-3">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[var(--color-success)]" aria-hidden="true" />
            <p className="text-sm">
              If that email exists, a reset link was sent. Check your inbox.
            </p>
          </div>
          <Link
            to="/login"
            className="block text-center text-sm text-indigo underline-offset-4 hover:underline"
          >
            Back to sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <TextField
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Button type="submit" className="h-11 w-full" disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            {loading ? "Sending…" : "Send reset link"}
          </Button>

          <p className="text-center text-sm">
            <Link to="/login" className="text-indigo underline-offset-4 hover:underline">
              Back to sign in
            </Link>
          </p>
        </form>
      )}
    </AuthLayout>
  )
}
