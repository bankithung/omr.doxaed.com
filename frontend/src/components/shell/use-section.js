import { useLocation } from "react-router-dom"
import { NAV } from "./nav-config"
import { useClass } from "@/features/class/useClass"
import { useTest } from "@/features/test/useTest"

/** Resolve the active rail section from the current pathname. */
export function useActiveSection() {
  const { pathname } = useLocation()
  return NAV.find((s) => s.match(pathname)) ?? NAV[0]
}

/**
 * Parse test-scoped context from a pathname.
 * Matches the exam workspace: bare /tests/:testId (overview) and
 * /tests/:testId/(questions|sheets|scan|review|results|analytics) +
 * /tests/:testId/students/:studentId. Returns { testId, current } or null.
 */
export function matchTestScope(pathname) {
  const m = pathname.match(
    /^\/tests\/([^/]+)(?:\/(questions|sheets|scan|review|results|analytics|students)(?:\/.*)?)?\/?$/
  )
  if (!m) return null
  const stage = m[2]
  // map page → lifecycle stage: bare → overview, questions → build,
  // sheets → generate, student-detail pages sit under "results".
  const current = !stage
    ? "overview"
    : stage === "questions"
      ? "build"
      : stage === "sheets"
        ? "generate"
        : stage === "students"
          ? "results"
          : stage
  return { testId: m[1], current }
}

/**
 * Parse org-scoped context from a pathname.
 * Matches /organizations/:id/(members|billing|audit). Returns { orgId, current } or null.
 */
export function matchOrgScope(pathname) {
  const m = pathname.match(
    /^\/org\/([^/]+)(?:\/(members|roles|usage|billing|settings|audit))?\/?$/,
  )
  if (!m) return null
  return { slug: m[1], current: m[2] || "dashboard" }
}

/**
 * Parse class-scoped (the Supabase "project") context from a pathname.
 * Matches /classes/:id and /classes/:id/<section>. `/classes/new` is NOT a class.
 * Returns { classId, current } or null. `current` defaults to "overview".
 */
export function matchClassScope(pathname) {
  const m = pathname.match(
    /^\/classes\/(\d+)(?:\/(groups|exams|students|subjects|access|settings))?\/?$/,
  )
  if (!m) return null
  return { classId: m[1], current: m[2] || "overview" }
}

/** Build the breadcrumb trail items for the TopBar from the URL + section. */
const CLASS_SECTION_LABEL = {
  overview: "Overview",
  groups: "Sub-groups",
  exams: "Exams",
  students: "Students",
  subjects: "Subjects",
  access: "Teacher access",
  settings: "Settings",
}

export function useBreadcrumbItems(section, { orgName } = {}) {
  const { pathname } = useLocation()
  // Pure path matches first; all hooks below run unconditionally (hooks rule).
  const classScope = matchClassScope(pathname)
  const testScope = matchTestScope(pathname)
  const cls = useClass(classScope ? classScope.classId : null)
  const test = useTest(testScope ? testScope.testId : null)
  const testClass = useClass(test?.class_group ?? null)
  const items = []

  if (classScope) {
    items.push({ label: "Classes", to: "/classes" })
    items.push({ label: cls?.name ?? "Class", to: `/classes/${classScope.classId}` })
    if (classScope.current !== "overview") {
      items.push({ label: CLASS_SECTION_LABEL[classScope.current] })
    }
    return items
  }

  const orgScope = matchOrgScope(pathname)
  if (orgScope) {
    items.push({ label: "Organizations", to: "/organizations" })
    items.push({ label: orgName ?? "Organization", to: `/org/${orgScope.slug}` })
    const leaf = {
      members: "Members",
      roles: "Roles & permissions",
      usage: "Usage",
      billing: "Billing",
      settings: "Settings",
      audit: "Audit",
    }[orgScope.current]
    if (orgScope.current !== "dashboard" && leaf) items.push({ label: leaf })
    return items
  }

  if (testScope) {
    items.push({ label: "Classes", to: "/classes" })
    if (testClass) items.push({ label: testClass.name, to: `/classes/${testClass.id}` })
    items.push({ label: test?.title ?? "Exam", to: `/tests/${testScope.testId}` })
    const leaf = {
      build: "Questions",
      generate: "Generate",
      scan: "Scan",
      review: "Review",
      results: "Results",
      analytics: "Analytics",
    }[testScope.current]
    if (leaf) items.push({ label: leaf })
    return items
  }

  // Default: just the active section label.
  items.push({ label: section.label, to: section.to })
  return items
}
