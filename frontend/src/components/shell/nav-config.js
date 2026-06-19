import {
  HomeIcon,
  LayersIcon,
  FileTextIcon,
  ScanLineIcon,
  BuildingIcon,
  SettingsIcon,
} from "lucide-react"

/**
 * NAV — single source of truth for the primary rail, the secondary panel,
 * the two-level mobile drawer, AND the Cmd-K "Go to" group.
 *
 * Each section:
 *   key     — stable id
 *   label   — rail tooltip + breadcrumb section label
 *   icon    — lucide icon component
 *   to      — default route the rail icon links to
 *   match   — (pathname) => boolean: derives the active section from the URL
 *   groups  — secondary-panel groups (null = childless section → no panel)
 *   footer  — pinned to the bottom of the rail when true
 *
 * NOTE on the two FIXED dead links:
 *   - The old RUN_NAV "Results" → "/tests" (no such route) is GONE: Results now
 *     lives only in the test-scoped panel under /tests/:testId/results.
 *   - The old ORG_ADMIN_NAV items all pointed at bare "/organizations" (needs an
 *     :id); they move into the org-scoped panel under /organizations/:id.
 */
export const NAV = [
  {
    key: "home",
    label: "Home",
    icon: HomeIcon,
    to: "/dashboard",
    match: (p) => p === "/" || p.startsWith("/dashboard"),
    groups: null, // single page → no secondary panel
  },
  {
    key: "workspace",
    label: "Workspace",
    icon: LayersIcon,
    to: "/classes",
    match: (p) => /^\/(classes|folders|rosters)/.test(p),
    groups: [
      {
        title: "Library",
        items: [
          { label: "Classes", to: "/classes", icon: FileTextIcon },
        ],
      },
    ],
  },
  {
    key: "tests",
    label: "Tests",
    icon: ScanLineIcon,
    to: "/scan",
    match: (p) => p.startsWith("/scan") || p.startsWith("/tests/"),
    groups: [
      {
        title: "Run",
        items: [{ label: "Scan", to: "/scan", icon: ScanLineIcon, end: true }],
      },
    ],
    // When /tests/:testId/* is active the panel is REPLACED by the test-scoped panel.
  },
  {
    key: "org",
    label: "Organization",
    icon: BuildingIcon,
    to: "/organizations",
    match: (p) => p.startsWith("/organizations"),
    groups: [
      {
        title: "Organizations",
        items: [
          { label: "All organizations", to: "/organizations", icon: BuildingIcon, end: true },
        ],
      },
    ],
    // When /organizations/:id/* is active the panel is REPLACED by the org-scoped panel.
  },
  {
    key: "settings",
    label: "Settings",
    icon: SettingsIcon,
    to: "/profile",
    footer: true, // pinned bottom of the rail
    match: (p) => p.startsWith("/profile"),
    groups: [
      {
        title: "Account",
        items: [{ label: "Profile", to: "/profile", end: true }],
      },
    ],
  },
]

/** Flatten every nav leaf (for the Cmd-K "Go to" group). */
export function flattenNavLeaves() {
  const out = []
  for (const section of NAV) {
    if (!section.groups) {
      out.push({ label: section.label, to: section.to, icon: section.icon })
      continue
    }
    for (const group of section.groups) {
      for (const item of group.items) {
        out.push({ label: item.label, to: item.to, icon: item.icon ?? section.icon })
      }
    }
  }
  return out
}
