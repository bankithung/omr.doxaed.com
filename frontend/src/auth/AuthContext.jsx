import { createContext, useContext, useEffect, useState } from "react"
import { authApi } from "@/api/client"

const AuthContext = createContext(null)

// Session-level cache for the initial GET /auth/me probe. The provider mounts
// once at the app root, but React StrictMode double-invokes effects in dev and
// any remount would otherwise re-probe. We resolve the user ONCE per session and
// reuse the in-flight promise / cached value; login() and logout() update it so
// it always reflects the current identity.
let mePromise = null
let cachedUser = null

function probeMe() {
  if (cachedUser) return Promise.resolve(cachedUser)
  if (!mePromise) {
    mePromise = authApi
      .me()
      .then((r) => {
        cachedUser = r.data
        return cachedUser
      })
      .catch(() => null)
      .finally(() => {
        mePromise = null
      })
  }
  return mePromise
}

export function AuthProvider({ children }) {
  const [user, setRawUser] = useState(cachedUser)
  const [loading, setLoading] = useState(true)

  // Keep the module-level session cache coherent with the live user state, so a
  // later remount (or StrictMode re-run) reuses the latest identity instead of
  // re-probing or reverting to stale data. Exposed as `setUser` for callers
  // (e.g. Profile after updateMe) so the public API is unchanged.
  function setUser(next) {
    cachedUser = typeof next === "function" ? next(cachedUser) : next
    setRawUser(next)
  }

  useEffect(() => {
    if (localStorage.getItem("access")) {
      probeMe()
        .then((u) => { if (u) setUser(u) })
        .finally(() => setLoading(false))
    } else setLoading(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function login(email, password) {
    const { data } = await authApi.login({ email, password })
    localStorage.setItem("access", data.access)
    localStorage.setItem("refresh", data.refresh)
    setUser(data.user)
  }

  // Mirror of login() for the Google Identity Services flow. Exchanges a Google
  // ID token (JWT credential) for our own {access, refresh, user} pair via the
  // backend /auth/google/ endpoint, then stores tokens identically to login().
  async function loginWithGoogle(idToken) {
    const { data } = await authApi.googleLogin(idToken)
    localStorage.setItem("access", data.access)
    localStorage.setItem("refresh", data.refresh)
    setUser(data.user)
  }

  async function logout() {
    const refresh = localStorage.getItem("refresh")
    try { if (refresh) await authApi.logout(refresh) } catch { /* ignore */ }
    localStorage.removeItem("access"); localStorage.removeItem("refresh")
    mePromise = null
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
