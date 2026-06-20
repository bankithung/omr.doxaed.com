import axios from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access")
  if (token) config.headers.Authorization = `Bearer ${token}`
  // Only ever send a NUMERIC org id. A stale/garbage activeOrg (e.g. the string
  // "undefined"/"null" left in localStorage) must never reach the server as a
  // header — it would otherwise break every scoped write ("could not create…").
  const org = localStorage.getItem("activeOrg")
  if (org && org !== "undefined" && org !== "null") config.headers["X-Organization-Id"] = org
  return config
})

let refreshPromise = null

// Public/auth routes that must NOT be force-redirected (avoids redirect loops).
const PUBLIC_PREFIXES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/accept-invite",
  "/terms",
  "/privacy",
  "/r/", // public result portal
]

// Session is dead (no/invalid refresh token): clear it and send the user to the
// login page. Without this, a 401 mid-session leaves the app broken-but-rendered
// — a security/UX hole. Hard-replace so the stale page isn't left in history.
function forceLogout() {
  try {
    localStorage.removeItem("access")
    localStorage.removeItem("refresh")
    localStorage.removeItem("activeOrg")
  } catch {
    /* ignore */
  }
  const path = window.location.pathname
  const onPublic = path === "/" || PUBLIC_PREFIXES.some((p) => path.startsWith(p))
  if (!onPublic) {
    window.location.replace("/login")
  }
}

// Auth endpoints handle their own errors (bad login, expired refresh) — never
// run the refresh-or-logout flow for them.
function isAuthCall(url = "") {
  return (
    url.includes("/auth/login") ||
    url.includes("/auth/register") ||
    url.includes("/auth/token/refresh") ||
    url.includes("/auth/google")
  )
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAuthCall(original.url)
    ) {
      original._retry = true
      const refresh = localStorage.getItem("refresh")
      if (!refresh) {
        forceLogout()
        return Promise.reject(error)
      }
      try {
        refreshPromise =
          refreshPromise || axios.post(`${baseURL}/auth/token/refresh/`, { refresh })
        const { data } = await refreshPromise
        refreshPromise = null
        localStorage.setItem("access", data.access)
        // Refresh-token ROTATION is on server-side: each refresh returns a NEW
        // refresh token and blacklists the old one. We MUST persist the new one,
        // or the next refresh uses a blacklisted token → 401 → spurious logout.
        if (data.refresh) localStorage.setItem("refresh", data.refresh)
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (e) {
        refreshPromise = null
        // Refresh failed → the session is unrecoverable. Log out + redirect.
        forceLogout()
        return Promise.reject(e)
      }
    }
    return Promise.reject(error)
  },
)

export const authApi = {
  register: (d) => api.post("/auth/register/", d),
  verifyEmail: (d) => api.post("/auth/verify-email/", d),
  login: (d) => api.post("/auth/login/", d),
  googleLogin: (idToken) => api.post("/auth/google/", { id_token: idToken }),
  logout: (refresh) => api.post("/auth/logout/", { refresh }),
  passwordReset: (email) => api.post("/auth/password-reset/", { email }),
  passwordResetConfirm: (d) => api.post("/auth/password-reset-confirm/", d),
  me: () => api.get("/auth/me/"),
  updateMe: (d) => api.patch("/auth/me/", d),
}
