import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { UserIcon, ShieldIcon, ArrowLeft } from "lucide-react"
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
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
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
  // Change password
  const [curPw, setCurPw] = useState("")
  const [newPw, setNewPw] = useState("")
  const [confirmPw, setConfirmPw] = useState("")
  const [changingPw, setChangingPw] = useState(false)
  // Delete account
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deletePw, setDeletePw] = useState("")
  const [deleting, setDeleting] = useState(false)

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

  async function handleChangePassword(e) {
    e.preventDefault()
    if (newPw.length < 8) {
      toast.error("New password must be at least 8 characters")
      return
    }
    if (newPw !== confirmPw) {
      toast.error("New passwords don't match")
      return
    }
    setChangingPw(true)
    try {
      await authApi.changePassword({ current_password: curPw, new_password: newPw })
      toast.success("Password changed")
      setCurPw("")
      setNewPw("")
      setConfirmPw("")
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to change password")
    } finally {
      setChangingPw(false)
    }
  }

  async function handleDeleteAccount() {
    if (!deletePw) {
      toast.error("Enter your password to confirm")
      return
    }
    setDeleting(true)
    try {
      await authApi.deleteAccount(deletePw)
      toast.success("Account deleted")
      // The account is gone server-side — clear the session locally and leave.
      localStorage.removeItem("access")
      localStorage.removeItem("refresh")
      localStorage.removeItem("activeOrg")
      setUser(null)
      navigate("/register")
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to delete account")
      setDeleting(false)
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
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-10 flex h-14 items-center border-b border-border bg-canvas px-4 sm:px-6">
        <button
          type="button"
          onClick={() => navigate("/organizations")}
          className="flex min-h-[40px] items-center gap-2 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden="true" /> All organizations
        </button>
      </header>
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
                ? "border-indigo text-foreground"
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
            <form onSubmit={handleChangePassword}>
              <CardHeader className="flex-col items-start gap-1">
                <CardTitle>Password</CardTitle>
                <CardDescription>
                  Change your password, you'll stay signed in on this device.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:max-w-sm">
                  <div className="space-y-1.5">
                    <Label htmlFor="cur-pw">Current password</Label>
                    <Input
                      id="cur-pw"
                      type="password"
                      autoComplete="current-password"
                      value={curPw}
                      onChange={(e) => setCurPw(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="new-pw">New password</Label>
                    <Input
                      id="new-pw"
                      type="password"
                      autoComplete="new-password"
                      value={newPw}
                      onChange={(e) => setNewPw(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="confirm-pw">Confirm new password</Label>
                    <Input
                      id="confirm-pw"
                      type="password"
                      autoComplete="new-password"
                      value={confirmPw}
                      onChange={(e) => setConfirmPw(e.target.value)}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleSendReset}
                  disabled={sendingReset || !user?.email}
                  className="text-xs font-medium text-indigo hover:underline disabled:opacity-50"
                >
                  {sendingReset ? "Sending…" : "Forgot your current password? Email a reset link"}
                </button>
              </CardContent>
              <CardFooter>
                <Button
                  type="submit"
                  size="sm"
                  className="min-h-[40px]"
                  disabled={changingPw || !curPw || !newPw}
                >
                  {changingPw ? "Changing…" : "Change password"}
                </Button>
              </CardFooter>
            </form>
          </Card>

          {/* ── Session ── */}
          <Card>
            <CardHeader className="flex-col items-start gap-1">
              <CardTitle>Sign out</CardTitle>
              <CardDescription>End your session on this device.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="min-h-[40px]" onClick={handleLogout}>
                Sign out
              </Button>
            </CardContent>
          </Card>

          {/* ── Danger zone ── */}
          <Card className="border-destructive/40">
            <CardHeader className="flex-col items-start gap-1">
              <CardTitle className="text-destructive">Delete account</CardTitle>
              <CardDescription>
                Permanently delete your account and every organization you own, with all
                their classes, exams and students. This can't be undone.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="destructive"
                className="min-h-[40px]"
                onClick={() => {
                  setDeletePw("")
                  setDeleteOpen(true)
                }}
              >
                Delete my account
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete-account confirmation */}
      <Dialog open={deleteOpen} onOpenChange={(o) => !deleting && setDeleteOpen(o)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete account</DialogTitle>
            <DialogDescription>
              This permanently deletes your account and everything you own. Enter your
              password to confirm.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="del-pw">Password</Label>
            <Input
              id="del-pw"
              type="password"
              autoComplete="current-password"
              value={deletePw}
              onChange={(e) => setDeletePw(e.target.value)}
              placeholder="Your password"
            />
          </div>
          <DialogFooter showCloseButton>
            <Button
              variant="destructive"
              onClick={handleDeleteAccount}
              disabled={deleting || !deletePw}
            >
              {deleting ? "Deleting…" : "Delete account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </PageShell>
    </div>
  )
}
