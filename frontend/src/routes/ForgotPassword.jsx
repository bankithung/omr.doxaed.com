import { useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

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
      toast.success("If that email exists, a reset link was sent.")
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">Reset password</h1>
          <p className="text-sm text-muted-foreground">
            Enter your email and we will send a reset link.
          </p>
        </div>

        {submitted ? (
          <div className="space-y-4">
            <p className="text-sm rounded-lg border border-border bg-muted/50 px-4 py-3">
              If that email exists, a reset link was sent. Check your inbox.
            </p>
            <Link
              to="/login"
              className="block text-sm text-center text-primary underline-offset-4 hover:underline"
            >
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Sending…" : "Send reset link"}
            </Button>

            <p className="text-sm text-center">
              <Link to="/login" className="text-primary underline-offset-4 hover:underline">
                Back to sign in
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
