import { lazy, Suspense } from "react"
import { Link, Route, Routes, useNavigate } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import ProtectedRoute from "@/auth/ProtectedRoute"
import RootRoute from "@/auth/RootRoute"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import { ChevronDownIcon, BuildingIcon } from "lucide-react"

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

function OrgSwitcher() {
  const { orgs, activeOrg, setActiveOrg } = useOrg()
  const label = activeOrg ? activeOrg.name : "Personal"

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-1 rounded-lg border border-border bg-background px-2.5 py-1 text-sm font-medium hover:bg-muted transition-colors">
        <BuildingIcon className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="max-w-[120px] truncate">{label}</span>
        <ChevronDownIcon className="size-3.5 shrink-0 text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuLabel>Context</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() => {
            setActiveOrg(null)
            window.location.reload()
          }}
          data-active={!activeOrg ? "" : undefined}
          className="data-[active]:font-semibold"
        >
          Personal
        </DropdownMenuItem>
        {orgs.length > 0 && <DropdownMenuSeparator />}
        {orgs.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onSelect={() => {
              setActiveOrg(org.id)
              window.location.reload()
            }}
            data-active={activeOrg?.id === org.id ? "" : undefined}
            className="data-[active]:font-semibold"
          >
            {org.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function Nav() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  return (
    <nav className="flex items-center gap-4 border-b px-4 py-3 text-sm">
      <Link to="/" className="font-semibold hover:text-primary">
        OMRFlow
      </Link>
      {user && (
        <>
          <Link to="/classes" className="text-muted-foreground hover:text-foreground">
            Classes
          </Link>
          <Link to="/rosters" className="text-muted-foreground hover:text-foreground">
            Rosters
          </Link>
          <Link to="/organizations" className="text-muted-foreground hover:text-foreground">
            Organizations
          </Link>
        </>
      )}

      <div className="ml-auto flex items-center gap-3">
        {user ? (
          <>
            <OrgSwitcher />
            <span className="hidden text-muted-foreground sm:inline">{user.email}</span>
            <Link to="/profile" className="hover:text-primary">
              Profile
            </Link>
            <button
              onClick={handleLogout}
              className="text-muted-foreground hover:text-foreground"
            >
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="hover:text-primary">
              Sign in
            </Link>
            <Link
              to="/register"
              className="rounded-lg bg-primary px-3 py-1 text-primary-foreground hover:bg-primary/80"
            >
              Register
            </Link>
          </>
        )}
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-background focus:px-4 focus:py-2 focus:text-foreground focus:shadow"
      >
        Skip to main content
      </a>
      <Toaster />
      <Nav />
      <main id="main">
        <Suspense fallback={<div className="p-8 text-muted-foreground">Loading…</div>}>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<RootRoute />} />
            <Route path="/health" element={<Health />} />
            <Route path="/style-guide" element={<StyleGuide />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/classes"
              element={
                <ProtectedRoute>
                  <Classes />
                </ProtectedRoute>
              }
            />
            <Route
              path="/classes/:id"
              element={
                <ProtectedRoute>
                  <TestList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/classes/:classId/tests/new"
              element={
                <ProtectedRoute>
                  <TestWizard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/rosters"
              element={
                <ProtectedRoute>
                  <Rosters />
                </ProtectedRoute>
              }
            />
            <Route
              path="/rosters/:id"
              element={
                <ProtectedRoute>
                  <RosterDetail />
                </ProtectedRoute>
              }
            />
            {/* Scan routes */}
            <Route
              path="/scan"
              element={
                <ProtectedRoute>
                  <Scan />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tests/:testId/scan"
              element={
                <ProtectedRoute>
                  <Scan />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tests/:testId/results"
              element={
                <ProtectedRoute>
                  <Results />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tests/:testId/review"
              element={
                <ProtectedRoute>
                  <ReviewQueue />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tests/:testId/analytics"
              element={
                <ProtectedRoute>
                  <Analytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizations"
              element={
                <ProtectedRoute>
                  <Organizations />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizations/:id/members"
              element={
                <ProtectedRoute>
                  <OrgMembers />
                </ProtectedRoute>
              }
            />
            <Route
              path="/accept-invite"
              element={
                <ProtectedRoute>
                  <AcceptInvite />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizations/:id/billing"
              element={
                <ProtectedRoute>
                  <Billing />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizations/:id/audit"
              element={
                <ProtectedRoute>
                  <OrgAudit />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tests/:testId/students/:studentId"
              element={
                <ProtectedRoute>
                  <StudentDetail />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
