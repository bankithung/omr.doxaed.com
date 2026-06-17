import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { toast } from "sonner"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [newPassword, setNewPassword] = useState("")
  const [loading, setLoading] = useState(false)

  const uid = searchParams.get("uid")
  const token = searchParams.get("token")

  async function handleSubmit(e) {
    e.preventDefault()

    if (!uid || !token) {
      toast.error("Invalid or expired reset link.")
      return
    }

    setLoading(true)
    try {
      await authApi.passwordResetConfirm({ uid, token, new_password: newPassword })
      toast.success("Password updated — you can now sign in")
      navigate("/login")
    } catch (err) {
      const data = err?.response?.data
      if (data) {
        const messages = Object.values(data).flat()
        toast.error(messages[0] ?? "Reset failed — the link may have expired")
      } else {
        toast.error("Reset failed — the link may have expired")
      }
    } finally {
      setLoading(false)
    }
  }

  if (!uid || !token) {
    return (
      <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm space-y-4 text-center">
          <h1 className="text-2xl font-bold text-destructive">Invalid link</h1>
          <p className="text-sm text-muted-foreground">
            This password reset link is invalid or has expired.
          </p>
          <Link
            to="/forgot-password"
            className="inline-block text-sm text-primary underline-offset-4 hover:underline"
          >
            Request a new link
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">Set new password</h1>
          <p className="text-sm text-muted-foreground">Choose a strong password for your account.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="new_password">New password</Label>
            <Input
              id="new_password"
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Saving…" : "Set password"}
          </Button>
        </form>

        <p className="text-sm text-center">
          <Link to="/login" className="text-primary underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
