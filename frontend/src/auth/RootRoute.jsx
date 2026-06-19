import { lazy, Suspense } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"
import BrandedSplash from "@/components/BrandedSplash"

const Landing = lazy(() => import("@/routes/Landing"))

export default function RootRoute() {
  const { user, loading } = useAuth()

  // While the initial me() probe is in flight, render a clean branded splash so a
  // logged-in user never sees the public landing flash, and a logged-out user
  // never sees a redirect bounce. AuthContext sets loading=false after me()
  // resolves/rejects, or immediately if there's no "access" token in localStorage.
  if (loading) {
    return <BrandedSplash />
  }

  // Redirect logged-in users to /dashboard so they get the full app shell.
  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <Suspense fallback={<BrandedSplash />}>
      <Landing />
    </Suspense>
  )
}
