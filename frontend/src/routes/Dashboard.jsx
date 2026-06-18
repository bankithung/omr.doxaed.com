import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { FileText, Users, ScanLine, BuildingIcon } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { listClasses } from "@/api/assessments"
import { listRosters } from "@/api/omr"
import { listOrgs } from "@/api/orgs"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { StatCard } from "@/components/ui/stat-card"

function normalize(data) {
  if (!data) return []
  const arr = data.results ?? data
  return Array.isArray(arr) ? arr : []
}

const QUICK_ACTIONS = [
  {
    icon: FileText,
    title: "Create a test",
    to: "/classes",
    body: "Build MCQ tests inside a class.",
  },
  {
    icon: Users,
    title: "Manage rosters",
    to: "/rosters",
    body: "Add students and roll numbers.",
  },
  {
    icon: ScanLine,
    title: "Scan sheets",
    to: "/scan",
    body: "Upload and auto-grade scans.",
  },
  {
    icon: BuildingIcon,
    title: "Organizations",
    to: "/organizations",
    body: "Invite teachers and manage seats.",
  },
]

export default function Dashboard() {
  const { user } = useAuth()
  const [classes, setClasses] = useState([])
  const [rosters, setRosters] = useState([])
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    ;(async () => {
      const [classesRes, rostersRes, orgsRes] = await Promise.allSettled([
        listClasses(),
        listRosters(),
        listOrgs(),
      ])
      if (!active) return
      let failed = false
      if (classesRes.status === "fulfilled") setClasses(normalize(classesRes.value))
      else failed = true
      if (rostersRes.status === "fulfilled") setRosters(normalize(rostersRes.value))
      else failed = true
      if (orgsRes.status === "fulfilled") setOrgs(normalize(orgsRes.value))
      else failed = true
      if (failed) toast.error("Some workspace data failed to load")
      setLoading(false)
    })()
    return () => {
      active = false
    }
  }, [])

  const isNewUser = !loading && classes.length === 0 && rosters.length === 0

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">
            {`Welcome back${user?.full_name ? `, ${user.full_name}` : ""}`}
          </h1>
          <p className="text-sm text-muted-foreground">Here's your grading workspace.</p>
        </div>
        <Button asChild>
          <Link to="/classes">Create a test</Link>
        </Button>
      </div>

      {/* Verify-email banner */}
      {user && user.is_email_verified === false && (
        <div className="rounded-xl border p-4 text-sm text-[var(--color-warning)]">
          Verify your email to unlock all features.{" "}
          <Link
            to="/profile"
            className="text-primary underline-offset-4 hover:underline"
          >
            Go to profile
          </Link>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK_ACTIONS.map(({ icon: Icon, title, to, body }) => (
          <Link
            key={to}
            to={to}
            className="rounded-xl border bg-card p-4 shadow-sm transition-colors hover:bg-muted/50"
          >
            <Icon className="size-5 text-muted-foreground" />
            <h2 className="mt-3 text-base font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{body}</p>
          </Link>
        ))}
      </div>

      {/* Stat row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Classes"
          value={loading ? undefined : classes.length}
          sub={
            <Link to="/classes" className="text-primary hover:underline">
              View all
            </Link>
          }
        />
        <StatCard
          label="Rosters"
          value={loading ? undefined : rosters.length}
          sub={
            <Link to="/rosters" className="text-primary hover:underline">
              View all
            </Link>
          }
        />
        <StatCard
          label="Organizations"
          value={loading ? undefined : orgs.length}
          sub={
            <Link to="/organizations" className="text-primary hover:underline">
              Manage
            </Link>
          }
        />
        <StatCard
          label="Account"
          value={user?.email ?? "—"}
          sub={user?.is_email_verified ? "Verified" : "Unverified"}
        />
      </div>

      {/* Recent lists OR global new-user empty state */}
      {isNewUser ? (
        <EmptyState
          title="Create your first test"
          description="Add a class, build an MCQ test, then generate and scan sheets to auto-grade."
          action={
            <Button asChild>
              <Link to="/classes">Create your first test</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Recent classes */}
          <div className="rounded-xl border">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-lg font-semibold">Recent classes</h2>
              <Link to="/classes" className="text-sm text-primary hover:underline">
                View all
              </Link>
            </div>
            {loading ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">Loading…</p>
            ) : classes.length === 0 ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">No classes yet.</p>
            ) : (
              <ul className="divide-y">
                {classes.slice(0, 5).map((cls) => (
                  <li key={cls.id}>
                    <Link
                      to={`/classes/${cls.id}`}
                      className="block px-4 py-3 transition-colors hover:bg-muted/50"
                    >
                      <span className="font-medium">{cls.name}</span>
                      <span className="mt-0.5 block text-sm text-muted-foreground">
                        {cls.description || <span className="italic">No description</span>}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Recent rosters */}
          <div className="rounded-xl border">
            <div className="flex items-center justify-between border-b px-4 py-3">
              <h2 className="text-lg font-semibold">Recent rosters</h2>
              <Link to="/rosters" className="text-sm text-primary hover:underline">
                View all
              </Link>
            </div>
            {loading ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">Loading…</p>
            ) : rosters.length === 0 ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">No rosters yet.</p>
            ) : (
              <ul className="divide-y">
                {rosters.slice(0, 5).map((roster) => (
                  <li key={roster.id}>
                    <Link
                      to={`/rosters/${roster.id}`}
                      className="block px-4 py-3 font-medium transition-colors hover:bg-muted/50"
                    >
                      {roster.name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
