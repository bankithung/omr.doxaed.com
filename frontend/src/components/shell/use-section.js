import { useLocation } from "react-router-dom"
import { NAV } from "./nav-config"

/** Resolve the active rail section from the current pathname. */
export function useActiveSection() {
  const { pathname } = useLocation()
  return NAV.find((s) => s.match(pathname)) ?? NAV[0]
}

/**
 * Parse test-scoped context from a pathname.
 * Matches /tests/:testId/(scan|review|results|analytics) and
 * /tests/:testId/students/:studentId. Returns { testId, current } or null.
 */
export function matchTestScope(pathname) {
  const m = pathname.match(
    /^\/tests\/([^/]+)\/(scan|review|results|analytics|students)/
  )
  if (!m) return null
  const stage = m[2]
  // student-detail pages sit under the "results" lifecycle stage for nav purposes
  const current = stage === "students" ? "results" : stage
  return { testId: m[1], current }
}

/**
 * Parse org-scoped context from a pathname.
 * Matches /organizations/:id/(members|billing|audit). Returns { orgId, current } or null.
 */
export function matchOrgScope(pathname) {
  const m = pathname.match(/^\/organizations\/([^/]+)\/(members|billing|audit)/)
  if (!m) return null
  return { orgId: m[1], current: m[2] }
}

/** Build the breadcrumb trail items for the TopBar from the URL + section. */
export function useBreadcrumbItems(section, { orgName } = {}) {
  const { pathname } = useLocation()
  const items = []

  const orgScope = matchOrgScope(pathname)
  if (orgScope) {
    items.push({ label: "Organizations", to: "/organizations" })
    items.push({ label: orgName ?? "Organization", to: `/organizations/${orgScope.orgId}/members` })
    const leaf = { members: "Members", billing: "Billing", audit: "Audit" }[orgScope.current]
    items.push({ label: leaf })
    return items
  }

  const testScope = matchTestScope(pathname)
  if (testScope) {
    items.push({ label: "Tests", to: "/scan" })
    const leaf = {
      scan: "Scan",
      review: "Review",
      results: "Results",
      analytics: "Analytics",
    }[testScope.current]
    items.push({ label: leaf })
    return items
  }

  // Default: just the active section label.
  items.push({ label: section.label, to: section.to })
  return items
}
