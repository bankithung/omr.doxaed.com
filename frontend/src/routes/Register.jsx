import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import AuthLayout, { LegalFooter } from "@/components/auth/AuthLayout"
import GoogleButton, { OrDivider } from "@/components/auth/GoogleButton"
import {
  FormBanner,
  PasswordField,
  PasswordStrength,
  TextField,
} from "@/components/auth/fields"

export default function Register() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [fieldErrors, setFieldErrors] = useState({})

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")
    setFieldErrors({})
    setLoading(true)
    try {
      await authApi.register({ email, password, full_name: fullName })
      toast.success("Account created — check your email to verify")
      navigate("/login")
    } catch (err) {
      const data = err?.response?.data
      if (data && typeof data === "object" && !Array.isArray(data)) {
        // Map per-field DRF errors (e.g. password / email) to inline messages.
        const fe = {}
        for (const [key, val] of Object.entries(data)) {
          if (key === "detail") continue
          fe[key] = Array.isArray(val) ? val[0] : String(val)
        }
        if (Object.keys(fe).length) setFieldErrors(fe)
        setError(data.detail ?? (Object.keys(fe).length ? "" : "Registration failed."))
      } else {
        setError("Registration failed.")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Create account"
      subtitle="Sign up to get started with DoxaEd OMR"
      footer={<LegalFooter />}
    >
      <GoogleButton label="Sign up with Google" />
      <OrDivider />

      <form onSubmit={handleSubmit} className="space-y-4">
        <FormBanner>{error}</FormBanner>

        <TextField
          id="full_name"
          label="Full name"
          type="text"
          autoComplete="name"
          placeholder="Jane Smith"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          error={fieldErrors.full_name}
        />

        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />

        <div className="space-y-2">
          <PasswordField
            id="password"
            label="Password"
            autoComplete="new-password"
            placeholder="••••••••"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrors.password}
          />
          <PasswordStrength password={password} />
        </div>

        <Button type="submit" className="h-11 w-full" disabled={loading}>
          {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
