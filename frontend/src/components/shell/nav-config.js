import { LayersIcon, SettingsIcon } from "lucide-react"

/**
 * NAV — primary rail sections. The product is **workspace-first**: the Classes
 * grid IS the home (no separate dashboard), and exams live inside a class (no
 * top-level "Tests"). Organization management is reached via the org switcher.
 *
 * Scoped panels (class / exam / organization) are resolved at runtime in
 * AppShell.usePanel (matchClassScope / matchTestScope / matchOrgScope), not here.
 *
 * Each section: key · label · icon · to · match(pathname) · groups · footer
 */
export const NAV = [
  {
    key: "workspace",
    label: "Classes",
    icon: LayersIcon,
    to: "/classes",
    match: (p) => /^\/(classes|folders|rosters|tests)/.test(p),
    groups: null, // the Classes grid is full-width; a class opens its own panel
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
