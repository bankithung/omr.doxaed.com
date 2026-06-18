import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import AuthLayout from "@/components/auth/AuthLayout"
import {
  FormBanner,
  PasswordField,
  PasswordStrength,
} from "@/components/auth/fields"

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [newPassword, setNewPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [fieldError, setFieldError] = useState("")

  const uid = searchParams.get("uid")
  const token = searchParams.get("token")

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")
    setFieldError("")

    if (!uid || !token) {
      setError("Invalid or expired reset link.")
      return
    }

    setLoading(true)
    try {
      await authApi.passwordResetConfirm({ uid, token, new_password: newPassword })
      toast.success("Password updated — you can now sign in")
      navigate("/login")
    } catch (err) {
      const data = err?.response?.data
      const pwErr = data?.new_password
      if (pwErr) {
        setFieldError(Array.isArray(pwErr) ? pwErr[0] : String(pwErr))
      } else {
        setError(data?.detail ?? "Reset failed — the link may have expired.")
      }
    } finally {
      setLoading(false)
    }
  }

  if (!uid || !token) {
    return (
      <AuthLayout
        title="Invalid link"
        subtitle="This password reset link is invalid or has expired."
      >
        <Link
          to="/forgot-password"
          className="inline-block text-sm text-primary underline-offset-4 hover:underline"
        >
          Request a new link
        </Link>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Set new password"
      subtitle="Choose a strong password for your account."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormBanner>{error}</FormBanner>

        <div className="space-y-2">
          <PasswordField
            id="new_password"
            label="New password"
            autoComplete="new-password"
            placeholder="••••••••"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            error={fieldError}
          />
          <PasswordStrength password={newPassword} />
        </div>

        <Button type="submit" className="h-11 w-full" disabled={loading}>
          {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {loading ? "Saving…" : "Set password"}
        </Button>

        <p className="text-center text-sm">
          <Link to="/login" className="text-primary underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
