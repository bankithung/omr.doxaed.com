import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { authApi } from "@/api/client"

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

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-4 text-center">
        {status === "pending" && (
          <>
            <h1 className="text-2xl font-bold">Verifying…</h1>
            <p className="text-sm text-muted-foreground">Please wait while we verify your email.</p>
          </>
        )}

        {status === "success" && (
          <>
            <h1 className="text-2xl font-bold text-green-600">Email verified</h1>
            <p className="text-sm text-muted-foreground">
              Your email has been verified. You can now log in.
            </p>
            <Link
              to="/login"
              className="inline-block text-sm text-primary underline-offset-4 hover:underline"
            >
              Go to sign in
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <h1 className="text-2xl font-bold text-destructive">Link invalid</h1>
            <p className="text-sm text-muted-foreground">
              This verification link is invalid or has expired.
            </p>
            <Link
              to="/login"
              className="inline-block text-sm text-primary underline-offset-4 hover:underline"
            >
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
