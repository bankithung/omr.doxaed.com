import { lazy, Suspense } from "react"
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import ProtectedRoute from "@/auth/ProtectedRoute"
import RootRoute from "@/auth/RootRoute"
import AppShell from "@/components/AppShell"

const Health = lazy(() => import("@/routes/Health"))
const StyleGuide = lazy(() => import("@/routes/StyleGuide"))
const Dashboard = lazy(() => import("@/routes/Dashboard"))
const Login = lazy(() => import("@/routes/Login"))
const Register = lazy(() => import("@/routes/Register"))
const VerifyEmail = lazy(() => import("@/routes/VerifyEmail"))
const ForgotPassword = lazy(() => import("@/routes/ForgotPassword"))
const ResetPassword = lazy(() => import("@/routes/ResetPassword"))
const Profile = lazy(() => import("@/routes/Profile"))
const Classes = lazy(() => import("@/routes/Classes"))
const Folders = lazy(() => import("@/routes/Folders"))
const FolderDetail = lazy(() => import("@/routes/FolderDetail"))
const TestList = lazy(() => import("@/routes/TestList"))
const TestWizard = lazy(() => import("@/routes/TestWizard"))
const Rosters = lazy(() => import("@/routes/Rosters"))
const RosterDetail = lazy(() => import("@/routes/RosterDetail"))
const Scan = lazy(() => import("@/routes/Scan"))
const Results = lazy(() => import("@/routes/Results"))
const ReviewQueue = lazy(() => import("@/routes/ReviewQueue"))
const Analytics = lazy(() => import("@/routes/Analytics"))
const Organizations = lazy(() => import("@/routes/Organizations"))
const OrgMembers = lazy(() => import("@/routes/OrgMembers"))
const OrgAudit = lazy(() => import("@/routes/OrgAudit"))
const AcceptInvite = lazy(() => import("@/routes/AcceptInvite"))
const Billing = lazy(() => import("@/routes/Billing"))
const StudentDetail = lazy(() => import("@/routes/StudentDetail"))
const PublicResult = lazy(() => import("@/routes/PublicResult"))

// ─── Minimal public nav (logged-out chrome) ───────────────────────────────────

function PublicNav() {
  return (
    <nav className="flex items-center gap-4 border-b px-4 py-3 text-sm">
      <Link to="/" className="font-semibold hover:text-primary">
        OMRFlow
      </Link>
      <div className="ml-auto flex items-center gap-3">
        <Link to="/login" className="hover:text-primary">
          Sign in
        </Link>
        <Link
          to="/register"
          className="rounded-lg bg-primary px-3 py-1.5 text-primary-foreground hover:bg-primary/80 transition-colors min-h-[40px] flex items-center"
        >
          Register
        </Link>
      </div>
    </nav>
  )
}

// ─── ShellProtectedRoute — wraps content in AppShell ─────────────────────────
// Reads org membership role to decide whether to surface admin nav items.
// The membership role is derived from the active org in OrgContext + the orgs
// list (which carries each org's member role from the API).

function ShellProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const { activeOrg, orgs } = useOrg()

  if (loading) {
    return <div className="p-8 text-muted-foreground">Loading…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  // Determine if the current user is admin in the active org.
  // The orgs list from the API includes a `role` field for the current user's membership.
  const activeOrgData = activeOrg
    ? orgs.find((o) => String(o.id) === String(activeOrg.id))
    : null
  const isAdmin = activeOrgData?.role === "admin"

  return (
    <AppShell isAdmin={isAdmin}>
      {children}
    </AppShell>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const { user } = useAuth()
  const location = useLocation()

  // Public portal pages (/r/:slug) and onboarding render without any shell
  const isPublicPortal = location.pathname.startsWith("/r/")

  // Show the minimal public nav only for logged-out users on non-portal pages
  const showPublicNav = !user && !isPublicPortal

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-background focus:px-4 focus:py-2 focus:text-foreground focus:shadow"
      >
        Skip to main content
      </a>
      <Toaster />

      {/* Public nav for logged-out auth/landing pages */}
      {showPublicNav && !isPublicPortal && <PublicNav />}

      <Suspense fallback={<div className="p-8 text-muted-foreground">Loading…</div>}>
        <Routes>
          {/* Public portal — no shell, no nav */}
          <Route path="/r/:slug" element={<PublicResult />} />

          {/* Root — redirects to dashboard (logged in) or landing (logged out) */}
          <Route
            path="/"
            element={
              <main id="main">
                <RootRoute />
              </main>
            }
          />

          {/* Public routes — minimal chrome (PublicNav above + page content) */}
          <Route path="/health" element={<main id="main"><Health /></main>} />
          <Route path="/style-guide" element={<main id="main"><StyleGuide /></main>} />
          <Route path="/login" element={<main id="main"><Login /></main>} />
          <Route path="/register" element={<main id="main"><Register /></main>} />
          <Route path="/verify-email" element={<main id="main"><VerifyEmail /></main>} />
          <Route path="/forgot-password" element={<main id="main"><ForgotPassword /></main>} />
          <Route path="/reset-password" element={<main id="main"><ResetPassword /></main>} />

          {/* Protected routes — wrapped in AppShell */}
          <Route
            path="/dashboard"
            element={
              <ShellProtectedRoute>
                <Dashboard />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ShellProtectedRoute>
                <Profile />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/classes"
            element={
              <ShellProtectedRoute>
                <Classes />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/classes/:id"
            element={
              <ShellProtectedRoute>
                <TestList />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/folders"
            element={
              <ShellProtectedRoute>
                <Folders />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/folders/:id"
            element={
              <ShellProtectedRoute>
                <FolderDetail />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/classes/:classId/tests/new"
            element={
              <ShellProtectedRoute>
                <TestWizard />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/rosters"
            element={
              <ShellProtectedRoute>
                <Rosters />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/rosters/:id"
            element={
              <ShellProtectedRoute>
                <RosterDetail />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/scan"
            element={
              <ShellProtectedRoute>
                <Scan />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/tests/:testId/scan"
            element={
              <ShellProtectedRoute>
                <Scan />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/tests/:testId/results"
            element={
              <ShellProtectedRoute>
                <Results />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/tests/:testId/review"
            element={
              <ShellProtectedRoute>
                <ReviewQueue />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/tests/:testId/analytics"
            element={
              <ShellProtectedRoute>
                <Analytics />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/organizations"
            element={
              <ShellProtectedRoute>
                <Organizations />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/organizations/:id/members"
            element={
              <ShellProtectedRoute>
                <OrgMembers />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/accept-invite"
            element={
              <ProtectedRoute>
                <main id="main">
                  <AcceptInvite />
                </main>
              </ProtectedRoute>
            }
          />
          <Route
            path="/organizations/:id/billing"
            element={
              <ShellProtectedRoute>
                <Billing />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/organizations/:id/audit"
            element={
              <ShellProtectedRoute>
                <OrgAudit />
              </ShellProtectedRoute>
            }
          />
          <Route
            path="/tests/:testId/students/:studentId"
            element={
              <ShellProtectedRoute>
                <StudentDetail />
              </ShellProtectedRoute>
            }
          />
        </Routes>
      </Suspense>
    </div>
  )
}
