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
  const { user } = useAuth()
  const [orgs, setOrgs] = useState([])
  const [activeOrgId, setActiveOrgId] = useState(() => localStorage.getItem(LS_KEY) || null)

  const refreshOrgs = useCallback(
    async ({ force = false } = {}) => {
      if (!user) return
      try {
        const list = await fetchOrgsDeduped(force)
        setOrgs(list)
      } catch {
        setOrgs([])
      }
    },
    [user],
  )

  useEffect(() => {
    if (user) {
      // Uses the session cache — subsequent provider re-renders / route changes
      // reuse the cached list rather than re-hitting the API.
      refreshOrgs()
    } else {
      clearOrgsCache()
      setOrgs([])
      setActiveOrgId(null)
      localStorage.removeItem(LS_KEY)
    }
  }, [user, refreshOrgs])

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
    <OrgContext.Provider value={{ activeOrgId, activeOrg, orgs, setActiveOrg, refreshOrgs }}>
      {children}
    </OrgContext.Provider>
  )
}

export const useOrg = () => useContext(OrgContext)
