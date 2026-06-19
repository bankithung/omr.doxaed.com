import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { useAuth } from "@/auth/AuthContext"
import { listOrgs } from "@/api/orgs"

const OrgContext = createContext(null)

const LS_KEY = "activeOrg"

// ─── Session-level org-list cache ────────────────────────────────────────────
// The org list is identical regardless of the active org (it's the set of orgs
// the *user* belongs to, with their role), so it does NOT need to be refetched
// when the active org changes or on every route mount. Several call sites
// (OrgContext effect, Organizations page, Dashboard, AcceptInvite) used to each
// fire their own GET /organizations/ on navigation — adding up to dozens of
// identical requests per journey.
//
// We dedupe with a module-level cache:
//   • `orgsCache`   — last successful result, reused on subsequent refreshOrgs()
//   • `orgsInFlight`— the pending promise, so concurrent callers share one request
//
// refreshOrgs({ force: true }) bypasses the cache — used after a mutation that
// changes membership (create org, accept invite) so the list is re-pulled.
// On logout the cache is cleared so the next login fetches fresh.
let orgsCache = null
let orgsInFlight = null

function fetchOrgsDeduped(force = false) {
  if (!force && orgsCache) return Promise.resolve(orgsCache)
  if (orgsInFlight) return orgsInFlight
  orgsInFlight = listOrgs()
    .then((data) => {
      orgsCache = data.results ?? data
      return orgsCache
    })
    .finally(() => {
      orgsInFlight = null
    })
  return orgsInFlight
}

function clearOrgsCache() {
  orgsCache = null
  orgsInFlight = null
}

export function OrgProvider({ children }) {
  const { user, loading: authLoading } = useAuth()
  const [orgs, setOrgs] = useState([])
  const [activeOrgId, setActiveOrgId] = useState(() => localStorage.getItem(LS_KEY) || null)
  // `loaded` flips true once the org list has resolved at least once — the
  // org-first gate must wait for this before deciding to send a user to create
  // an organization (otherwise it would redirect during the initial fetch).
  const [loaded, setLoaded] = useState(false)

  const refreshOrgs = useCallback(
    async ({ force = false } = {}) => {
      if (!user) return
      try {
        const list = await fetchOrgsDeduped(force)
        setOrgs(list)
        // Drop a stale/garbage stored active org: if the saved id is not one of
        // the user's CURRENT memberships, clear it so the api interceptor never
        // sends a stale `X-Organization-Id`. localStorage persists across logins,
        // so a prior session's (or a deleted/removed) org id can linger and make
        // every scoped write — e.g. "create class" — fail with 403/400.
        const stored = localStorage.getItem(LS_KEY)
        if (stored && !list.some((o) => String(o.id) === String(stored))) {
          localStorage.removeItem(LS_KEY)
          setActiveOrgId(null)
        }
        // Org-first (Supabase-style): never run in loose/personal scope when the
        // user belongs to an org — auto-select one so the app always has an
        // active organization. Users with NO org are routed to create one.
        const after = localStorage.getItem(LS_KEY)
        if (!after && list.length > 0) {
          localStorage.setItem(LS_KEY, String(list[0].id))
          setActiveOrgId(String(list[0].id))
        }
      } catch {
        setOrgs([])
      } finally {
        setLoaded(true)
      }
    },
    [user],
  )

  useEffect(() => {
    // While the auth probe is in flight, do NOTHING. `user` is briefly null during
    // loading; clearing activeOrg here would wipe a valid saved org on every page
    // refresh and bounce the user to a different organization.
    if (authLoading) return
    if (user) {
      // Uses the session cache — subsequent provider re-renders / route changes
      // reuse the cached list rather than re-hitting the API.
      refreshOrgs()
    } else {
      clearOrgsCache()
      setOrgs([])
      setActiveOrgId(null)
      setLoaded(false)
      localStorage.removeItem(LS_KEY)
    }
  }, [user, authLoading, refreshOrgs])

  function setActiveOrg(id) {
    if (id) {
      localStorage.setItem(LS_KEY, id)
    } else {
      localStorage.removeItem(LS_KEY)
    }
    // Switching org only changes which X-Organization-Id header subsequent
    // requests carry (read live from localStorage in the api interceptor); the
    // org LIST itself is unchanged, so we deliberately do NOT refetch it here.
    setActiveOrgId(id || null)
  }

  const activeOrg = orgs.find((o) => String(o.id) === String(activeOrgId)) || null

  return (
    <OrgContext.Provider value={{ activeOrgId, activeOrg, orgs, loaded, setActiveOrg, refreshOrgs }}>
      {children}
    </OrgContext.Provider>
  )
}

export const useOrg = () => useContext(OrgContext)
