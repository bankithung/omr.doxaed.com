import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { UserIcon, ShieldIcon } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { cn } from "@/lib/utils"

// Settings sub-nav sections. `id` doubles as the scroll anchor + active key.
const SECTIONS = [
  { id: "account", label: "Account", icon: UserIcon },
  { id: "security", label: "Security", icon: ShieldIcon },
]

/**
 * SettingsRow — a description-left / control-right settings row.
 * Stacks on mobile, splits on sm+.
 */
function SettingsRow({ title, description, children }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <div className="min-w-0 sm:max-w-xs">
        <p className="text-sm font-medium">{title}</p>
        {description && (
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="w-full sm:max-w-xs sm:flex-1">{children}</div>
    </div>
  )
}

export default function Profile() {
  const { user, setUser, logout } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState(user?.full_name ?? "")
  const [saving, setSaving] = useState(false)
  const [sendingReset, setSendingReset] = useState(false)
  const [active, setActive] = useState("account")

  // Save is disabled until the form is dirty (name differs from the stored value).
  const dirty = fullName.trim() !== (user?.full_name ?? "").trim()

  async function handleSave(e) {
    e.preventDefault()
    if (!dirty) return
    setSaving(true)
    try {
      const resp = await authApi.updateMe({ full_name: fullName.trim() })
      setUser(resp.data)
      toast.success("Profile saved")
    } catch {
      toast.error("Failed to save profile")
    } finally {
      setSaving(false)
    }
  }

  async function handleSendReset() {
    if (!user?.email) return
    setSendingReset(true)
    try {
      await authApi.passwordReset(user.email)
      toast.success("Password reset link sent to your email")
    } catch {
      toast.error("Failed to send reset link")
    } finally {
      setSendingReset(false)
    }
  }

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  function goTo(id) {
    setActive(id)
    document
      .getElementById(`settings-${id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <PageShell>
      <PageHeader title="Profile" description="Manage your account settings" />

      {/* Mobile sub-nav: horizontal tabs */}
      <nav
        aria-label="Settings sections"
        className="-mb-4 flex gap-1 border-b border-border lg:hidden"
      >
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => goTo(s.id)}
            aria-current={active === s.id ? "true" : undefined}
            className={cn(
              "min-h-[40px] border-b-2 px-3 text-sm font-medium transition-colors",
              active === s.id
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <div className="grid gap-8 lg:grid-cols-[180px_1fr]">
        {/* Desktop sub-nav: vertical */}
        <nav
          aria-label="Settings sections"
          className="hidden lg:block"
        >
          <ul className="sticky top-20 space-y-1">
            {SECTIONS.map((s) => {
              const Icon = s.icon
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => goTo(s.id)}
                    aria-current={active === s.id ? "true" : undefined}
                    className={cn(
                      "flex min-h-[40px] w-full items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors",
                      active === s.id
                        ? "bg-nav-active-bg text-nav-active-fg"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                    {s.label}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Settings sections */}
        <div className="min-w-0 space-y-6">
          {/* ── Account ── */}
          <Card id="settings-account">
            <form onSubmit={handleSave}>
              <CardHeader className="flex-col items-start gap-1">
                <CardTitle>Account</CardTitle>
                <CardDescription>
                  Your personal details and email status.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <SettingsRow
                  title="Full name"
                  description="The name shown across your workspace."
                >
                  <Input
                    id="full_name"
                    type="text"
                    autoComplete="name"
                    placeholder="Your name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </SettingsRow>

                <SettingsRow
                  title="Email"
                  description="Used to sign in and for notifications."
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Input
                      id="email"
                      type="email"
                      value={user?.email ?? ""}
                      readOnly
                      disabled
                      className="flex-1"
                    />
                    {user?.is_email_verified ? (
                      <Badge variant="success">Verified</Badge>
                    ) : (
                      <Badge variant="warning">Unverified</Badge>
                    )}
                  </div>
                </SettingsRow>
              </CardContent>
              <CardFooter>
                <Button
                  type="submit"
                  size="sm"
                  className="min-h-[40px]"
                  disabled={saving || !dirty}
                >
                  {saving ? "Saving…" : "Save changes"}
                </Button>
              </CardFooter>
            </form>
          </Card>

          {/* ── Security ── */}
          <Card id="settings-security">
            <CardHeader className="flex-col items-start gap-1">
              <CardTitle>Security</CardTitle>
              <CardDescription>
                Manage your password and account access.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <SettingsRow
                title="Password"
                description="We'll email you a secure link to set a new password."
              >
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="min-h-[40px]"
                  onClick={handleSendReset}
                  disabled={sendingReset || !user?.email}
                >
                  {sendingReset ? "Sending…" : "Send password reset link"}
                </Button>
              </SettingsRow>
            </CardContent>
          </Card>

          {/* ── Danger zone ── */}
          <Card className="border-destructive/30">
            <CardHeader className="flex-col items-start gap-1">
              <CardTitle>Sign out</CardTitle>
              <CardDescription>
                End your session on this device.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                className="min-h-[40px]"
                onClick={handleLogout}
              >
                Sign out
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageShell>
  )
}
