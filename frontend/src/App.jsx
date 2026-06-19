import { lazy, Suspense } from "react"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import ProtectedRoute from "@/auth/ProtectedRoute"
import RootRoute from "@/auth/RootRoute"
import AppShell from "@/components/AppShell"
import AppShellSkeleton from "@/components/AppShellSkeleton"
import BrandedSplash from "@/components/BrandedSplash"

const Health = lazy(() => import("@/routes/Health"))
const StyleGuide = lazy(() => import("@/routes/StyleGuide"))
const Dashboard = lazy(() => import("@/routes/Dashboard"))
const Onboarding = lazy(() => import("@/routes/Onboarding"))
const Login = lazy(() => import("@/routes/Login"))
const Register = lazy(() => import("@/routes/Register"))
const VerifyEmail = lazy(() => import("@/routes/VerifyEmail"))
const ForgotPassword = lazy(() => import("@/routes/ForgotPassword"))
const ResetPassword = lazy(() => import("@/routes/ResetPassword"))
const Terms = lazy(() => import("@/routes/Terms"))
const Privacy = lazy(() => import("@/routes/Privacy"))
const Pricing = lazy(() => import("@/routes/Pricing"))
const Features = lazy(() => import("@/routes/Features"))
const About = lazy(() => import("@/routes/About"))
const Contact = lazy(() => import("@/routes/Contact"))
const HowItWorksPage = lazy(() => import("@/routes/HowItWorksPage"))
const Security = lazy(() => import("@/routes/Security"))
const FAQ = lazy(() => import("@/routes/FAQ"))
const Help = lazy(() => import("@/routes/Help"))
const NotFound = lazy(() => import("@/routes/NotFound"))
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

// ─── ShellProtectedRoute — wraps content in AppShell ─────────────────────────
// Reads org membership role to decide whether to surface admin nav items.
// The membership role is derived from the active org in OrgContext + the orgs
// list (which carries each org's member role from the API).

function ShellProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const { activeOrg, orgs } = useOrg()

  if (loading) {
    return <AppShellSkeleton />
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
  const location = useLocation()

  // Public portal pages (/r/:slug) and onboarding render without any shell
  const isPublicPortal = location.pathname.startsWith("/r/")

  // Public (non-app) paths that ship their OWN full-width chrome: the landing
  // ("/"), the marketing pages (PublicLayout = LandingNav + Footer), and the
  // auth + legal pages (the same LandingNav header, via AuthLayout / LegalLayout).
  // Used only to pick the right refresh fallback (branded splash, not the
  // app-shell skeleton).
  const SELF_CHROMED = [
    "/",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/terms",
    "/privacy",
    "/pricing",
    "/features",
    "/about",
    "/contact",
    "/security",
    "/faq",
    "/help",
    "/how-it-works",
  ]

  // Route-aware Suspense fallback: app (shell) routes show the app-shell skeleton
  // on refresh; public/auth/landing routes show a clean branded splash. We treat
  // the self-chromed public paths + the public portal as "public"; everything
  // else is an in-app (shell) route.
  const isPublicRoute =
    isPublicPortal ||
    SELF_CHROMED.includes(location.pathname) ||
    location.pathname === "/onboarding" ||
    location.pathname === "/accept-invite" ||
    location.pathname === "/health" ||
    location.pathname === "/verify-email" ||
    location.pathname === "/style-guide"
  const SuspenseFallback = isPublicRoute ? <BrandedSplash /> : <AppShellSkeleton />

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-background focus:px-4 focus:py-2 focus:text-foreground focus:shadow"
      >
        Skip to main content
      </a>
      <Toaster />

      <Suspense fallback={SuspenseFallback}>
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
          <Route path="/terms" element={<main id="main"><Terms /></main>} />
          <Route path="/privacy" element={<main id="main"><Privacy /></main>} />

          {/* Public marketing pages — ship their own PublicLayout (landing nav +
              footer + <main id="main">), so they render bare like the landing,
              with no AppShell and no extra <main> wrapper. */}
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/features" element={<Features />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/security" element={<Security />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/help" element={<Help />} />
          <Route path="/how-it-works" element={<HowItWorksPage />} />

          {/* Onboarding — full-screen wizard, no AppShell (login required) */}
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <main id="main">
                  <Onboarding />
                </main>
              </ProtectedRoute>
            }
          />

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

          {/* Catch-all 404 — MUST be last. Branded NotFound in PublicLayout. */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </div>
  )
}
