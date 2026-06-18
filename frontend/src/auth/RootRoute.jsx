import { lazy, Suspense } from "react"
import { useAuth } from "@/auth/AuthContext"

const Landing = lazy(() => import("@/routes/Landing"))
const Dashboard = lazy(() => import("@/routes/Dashboard"))

export default function RootRoute() {
  const { user, loading } = useAuth()

  // While the initial me() probe is in flight, render a neutral placeholder so a
  // logged-in user never sees the public landing flash, and a logged-out user
  // never sees a redirect bounce. AuthContext sets loading=false after me()
  // resolves/rejects, or immediately if there's no "access" token in localStorage.
  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-57px)] items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    )
  }

  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-57px)] items-center justify-center text-sm text-muted-foreground">
          Loading…
        </div>
      }
    >
      {user ? <Dashboard /> : <Landing />}
    </Suspense>
  )
}
