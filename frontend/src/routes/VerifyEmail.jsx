import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { CheckCircle2, Loader2, XCircle } from "lucide-react"
import { authApi } from "@/api/client"
import AuthLayout from "@/components/auth/AuthLayout"

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState("pending") // "pending" | "success" | "error"

  useEffect(() => {
    const uid = searchParams.get("uid")
    const token = searchParams.get("token")

    if (!uid || !token) {
      setStatus("error")
      return
    }

    authApi
      .verifyEmail({ uid, token })
      .then(() => setStatus("success"))
      .catch(() => setStatus("error"))
  }, [searchParams])

  const subtitle =
    status === "pending"
      ? "Confirming your email address."
      : status === "success"
        ? "Your account is ready to go."
        : "We couldn't confirm this email."

  return (
    <AuthLayout title="Verify email" subtitle={subtitle}>
      {status === "pending" && (
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <Loader2 className="size-8 animate-spin text-indigo" aria-hidden="true" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold">Verifying…</h2>
            <p className="text-sm text-muted-foreground">
              Please wait while we verify your email.
            </p>
          </div>
        </div>
      )}

      {status === "success" && (
        <div className="space-y-5">
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-[color-mix(in_oklch,var(--color-success)_14%,transparent)]">
              <CheckCircle2 className="size-7 text-[var(--color-success)]" aria-hidden="true" />
            </span>
            <div className="space-y-1">
              <h2 className="text-lg font-bold">Email verified</h2>
              <p className="text-sm text-muted-foreground">
                Your email has been verified. You can now log in.
              </p>
            </div>
          </div>
          <Link
            to="/login"
            className="block text-center text-sm text-indigo underline-offset-4 hover:underline"
          >
            Continue to sign in
          </Link>
        </div>
      )}

      {status === "error" && (
        <div className="space-y-5">
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10">
              <XCircle className="size-7 text-destructive" aria-hidden="true" />
            </span>
            <div className="space-y-1">
              <h2 className="text-lg font-bold">Link invalid</h2>
              <p className="text-sm text-muted-foreground">
                This verification link is invalid or has expired.
              </p>
            </div>
          </div>
          <Link
            to="/login"
            className="block text-center text-sm text-indigo underline-offset-4 hover:underline"
          >
            Back to sign in
          </Link>
        </div>
      )}
    </AuthLayout>
  )
}
