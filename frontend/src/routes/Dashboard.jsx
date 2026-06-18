import { useEffect, useState } from "react"
import { Link, Navigate } from "react-router-dom"
import { toast } from "sonner"
import { FileText, Users, ScanLine, BuildingIcon, X } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import { listClasses } from "@/api/assessments"
import { listRosters } from "@/api/omr"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { StatCard } from "@/components/ui/stat-card"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card"
import {
  CardGridSkeleton,
  ListRowSkeleton,
} from "@/components/ui/skeletons"

const ONBOARDED_KEY = "omrflow_onboarded"
const WELCOME_DISMISSED_KEY = "omrflow_welcome_dismissed"

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
  // Org count comes from OrgContext (session-cached) rather than an independent
  // GET /organizations/ on every dashboard visit — org-switch navigates here, so
  // a per-visit fetch was a major source of redundant org calls.
  const { orgs } = useOrg()
  const [classes, setClasses] = useState([])
  const [rosters, setRosters] = useState([])
  const [loading, setLoading] = useState(true)

  // First-run redirect: send brand-new users to the onboarding wizard.
  // Read synchronously so the guard runs before any fetch / paint. The wizard
  // sets `omrflow_onboarded` on BOTH finish and skip, so this never loops.
  // Gated to the Dashboard route only — other routes are never redirected.
  const needsOnboarding =
    typeof localStorage !== "undefined" && !localStorage.getItem(ONBOARDED_KEY)

  // One-time "Workspace ready" banner — shown after onboarding until dismissed.
  const [welcomeDismissed, setWelcomeDismissed] = useState(
    () =>
      typeof localStorage === "undefined" ||
      !!localStorage.getItem(WELCOME_DISMISSED_KEY),
  )

  function dismissWelcome() {
    try {
      localStorage.setItem(WELCOME_DISMISSED_KEY, "1")
    } catch { /* ignore storage failures */ }
    setWelcomeDismissed(true)
  }

  useEffect(() => {
    if (needsOnboarding) return undefined
    let active = true
    ;(async () => {
      const [classesRes, rostersRes] = await Promise.allSettled([
        listClasses(),
        listRosters(),
      ])
      if (!active) return
      let failed = false
      if (classesRes.status === "fulfilled") setClasses(normalize(classesRes.value))
      else failed = true
      if (rostersRes.status === "fulfilled") setRosters(normalize(rostersRes.value))
      else failed = true
      if (failed) toast.error("Some workspace data failed to load")
      setLoading(false)
    })()
    return () => {
      active = false
    }
  }, [needsOnboarding])

  // Redirect brand-new users into the wizard (only from this route).
  if (needsOnboarding) {
    return <Navigate to="/onboarding" replace />
  }

  const isNewUser = !loading && classes.length === 0 && rosters.length === 0

  return (
    <PageShell>
      {/* One-time "Workspace ready" banner — shown post-onboarding */}
      {!welcomeDismissed && (
        <div className="flex items-start justify-between gap-4 rounded-lg border border-[var(--color-success)]/40 bg-card p-4">
          <div>
            <p className="text-sm font-semibold text-[var(--color-success)]">Workspace ready</p>
            <p className="mt-0.5 text-sm text-muted-foreground">
              You're all set. Create a test or scan sheets whenever you're ready.
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={dismissWelcome}
            aria-label="Dismiss"
          >
            <X className="size-4" />
          </Button>
        </div>
      )}

      <PageHeader
        title={`Welcome back${user?.full_name ? `, ${user.full_name}` : ""}`}
        description="Here's your grading workspace."
        actions={
          <Button asChild>
            <Link to="/classes">Create a test</Link>
          </Button>
        }
      />

      {/* Verify-email banner */}
      {user && user.is_email_verified === false && (
        <div className="rounded-lg border border-border p-4 text-sm text-[var(--color-warning)]">
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
            className="motion-safe-card rounded-lg border border-border bg-card p-4 outline-none hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <Icon className="size-5 text-muted-foreground" />
            <h2 className="mt-3 text-base font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{body}</p>
          </Link>
        ))}
      </div>

      {/* Stat row */}
      {loading ? (
        <CardGridSkeleton count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Classes"
            value={classes.length}
            sub={
              <Link to="/classes" className="text-primary hover:underline">
                View all
              </Link>
            }
          />
          <StatCard
            label="Rosters"
            value={rosters.length}
            sub={
              <Link to="/rosters" className="text-primary hover:underline">
                View all
              </Link>
            }
          />
          <StatCard
            label="Organizations"
            value={orgs.length}
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
      )}

      {/* Recent lists OR global new-user empty state */}
      {isNewUser ? (
        <EmptyState
          icon={FileText}
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
          <Card>
            <CardHeader>
              <CardTitle>Recent classes</CardTitle>
              <Link to="/classes" className="text-sm text-primary hover:underline">
                View all
              </Link>
            </CardHeader>
            {loading ? (
              <div className="py-2" aria-hidden="true">
                {[0, 1, 2].map((i) => (
                  <ListRowSkeleton key={i} />
                ))}
              </div>
            ) : classes.length === 0 ? (
              <CardContent>
                <p className="text-sm text-muted-foreground">No classes yet.</p>
              </CardContent>
            ) : (
              <ul className="divide-y divide-border">
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
          </Card>

          {/* Recent rosters */}
          <Card>
            <CardHeader>
              <CardTitle>Recent rosters</CardTitle>
              <Link to="/rosters" className="text-sm text-primary hover:underline">
                View all
              </Link>
            </CardHeader>
            {loading ? (
              <div className="py-2" aria-hidden="true">
                {[0, 1, 2].map((i) => (
                  <ListRowSkeleton key={i} />
                ))}
              </div>
            ) : rosters.length === 0 ? (
              <CardContent>
                <p className="text-sm text-muted-foreground">No rosters yet.</p>
              </CardContent>
            ) : (
              <ul className="divide-y divide-border">
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
          </Card>
        </div>
      )}
    </PageShell>
  )
}
