import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Plus, LogOut, Building2 } from "lucide-react"
import { useOrg } from "@/org/OrgContext"
import { useAuth } from "@/auth/AuthContext"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

const TYPE_LABEL = {
  personal: "Personal",
  school: "School",
  college: "College",
  university: "University",
  coaching: "Coaching",
  other: "Other",
}

function OrgCard({ org, onOpen }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(org)}
      className="group flex items-center gap-3 rounded-xl border border-border bg-surface-1 p-4 text-left transition-colors hover:border-primary/50 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-sm font-bold text-primary">
        {(org.name?.[0] ?? "O").toUpperCase()}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold group-hover:text-primary">{org.name}</p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {org.type && <Badge variant="neutral">{TYPE_LABEL[org.type] ?? org.type}</Badge>}
          {org.role && <Badge variant="info" className="capitalize">{org.role}</Badge>}
        </div>
      </div>
    </button>
  )
}

// L0 — the Organizations entry page (no app shell). The user picks an org to
// enter, or creates one. Mirrors Supabase's "choose an organization" landing.
export default function OrgList() {
  const navigate = useNavigate()
  const { orgs, loaded, setActiveOrg, refreshOrgs } = useOrg()
  const { user, logout } = useAuth()
  const [refreshing, setRefreshing] = useState(false)

  const reload = useCallback(() => {
    setRefreshing(true)
    refreshOrgs({ force: true }).finally(() => setRefreshing(false))
  }, [refreshOrgs])

  useEffect(() => {
    reload()
  }, [reload])

  function openOrg(org) {
    setActiveOrg(String(org.id))
    navigate("/classes")
  }

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  const loading = !loaded || refreshing

  return (
    <div className="min-h-screen bg-canvas">
      {/* Minimal top bar — no sidebar at this level */}
      <header className="flex h-14 items-center justify-between border-b border-border px-4 sm:px-6">
        <span className="text-sm font-bold tracking-tight text-primary">DoxaEd OMR</span>
        <div className="flex items-center gap-3">
          {user?.email && (
            <span className="hidden max-w-[180px] truncate text-sm text-muted-foreground sm:block">
              {user.email}
            </span>
          )}
          <Button variant="ghost" size="sm" className="min-h-[40px]" onClick={handleLogout}>
            <LogOut className="size-4" aria-hidden="true" /> Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <div className="mb-6 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Organizations</h1>
            <p className="mt-1 text-sm text-muted-foreground">Choose an organization to open, or create a new one.</p>
          </div>
          <Button onClick={() => navigate("/organizations/new")} className="min-h-[40px] shrink-0">
            <Plus className="size-4" aria-hidden="true" /> New organization
          </Button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[68px] w-full rounded-xl" />
            ))}
          </div>
        ) : orgs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-10 text-center">
            <Building2 className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
            <p className="mt-3 font-medium">No organizations yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Create your first organization to start adding classes, exams and your team.
            </p>
            <Button className="mt-4" onClick={() => navigate("/organizations/new")}>
              <Plus className="size-4" aria-hidden="true" /> New organization
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {orgs.map((org) => (
              <OrgCard key={org.id} org={org} onOpen={openOrg} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
