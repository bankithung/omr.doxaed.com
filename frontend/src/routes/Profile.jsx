import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { useAuth } from "@/auth/AuthContext"
import { authApi } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function Profile() {
  const { user, setUser, logout } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState(user?.full_name ?? "")
  const [saving, setSaving] = useState(false)

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const resp = await authApi.updateMe({ full_name: fullName })
      setUser(resp.data)
      toast.success("Profile saved")
    } catch {
      toast.error("Failed to save profile")
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  return (
    <div className="flex min-h-[calc(100vh-57px)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">Profile</h1>
          <p className="text-sm text-muted-foreground">{user?.email}</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Email status:</span>
          {user?.is_email_verified ? (
            <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
              Verified
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
              Unverified
            </span>
          )}
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="full_name">Full name</Label>
            <Input
              id="full_name"
              type="text"
              autoComplete="name"
              placeholder="Your name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <Button type="submit" className="w-full" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </form>

        <div className="border-t pt-4">
          <Button variant="destructive" className="w-full" onClick={handleLogout}>
            Sign out
          </Button>
        </div>
      </div>
    </div>
  )
}
