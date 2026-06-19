import { useEffect, useState } from "react"
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom"

import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import { cn } from "@/lib/utils"

import { NAV } from "@/components/shell/nav-config"
import {
  useActiveSection,
  matchTestScope,
  matchOrgScope,
  matchClassScope,
  useBreadcrumbItems,
} from "@/components/shell/use-section"
import { useClass } from "@/features/class/useClass"
import { childKindLabel, pluralize } from "@/features/class/typePresets"
import { STAGES, stageHref } from "@/components/ui/test-progress-rail"

import { Button } from "@/components/ui/button"
import { Breadcrumb } from "@/components/ui/breadcrumb"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ThemeToggle } from "@/components/ThemeToggle"
import CommandMenu from "@/components/CommandMenu"
import {
  HomeIcon,
  ScanLineIcon,
  FileTextIcon,
  BuildingIcon,
  SearchIcon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  MenuIcon,
  ChevronsUpDownIcon,
  CheckIcon,
  PlusIcon,
  UserIcon,
  LogOutIcon,
  ArrowLeftIcon,
} from "lucide-react"

const PANEL_COLLAPSE_KEY = "nav.panel.collapsed"

// ─── Bottom tab bar items (mobile) ────────────────────────────────────────────
// NOTE: the old "Results" → "/tests" tab was a DEAD link; repointed to "/scan".
const BOTTOM_TABS = [
  { label: "Home", to: "/dashboard", icon: HomeIcon },
  { label: "Classes", to: "/classes", icon: FileTextIcon },
  { label: "Scan", to: "/scan", icon: ScanLineIcon },
  { label: "Org", to: "/organizations", icon: BuildingIcon },
]

// ─── helpers: initials for avatar ─────────────────────────────────────────────

function initials(user) {
  const name = user?.name || user?.first_name || user?.email || "?"
  const parts = String(name).trim().split(/[\s@.]+/).filter(Boolean)
  if (parts.length === 0) return "?"
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

// ─── NavSection — uppercase-label group of leaves (shared) ─────────────────────

function NavSection({ title, items, onNavigate }) {
  return (
    <div className="px-2 py-1">
      {title && (
        <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-widest text-sidebar-foreground/50 select-none">
          {title}
        </p>
      )}
      <ul className="space-y-0.5">
        {items.map(({ label, to, icon: Icon, end, badge }) => (
          <li key={to + label}>
            <NavLink
              to={to}
              end={end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "flex min-h-[40px] items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium motion-safe-card outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                  isActive
                    ? "bg-nav-active-bg text-nav-active-fg"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {badge != null ? (
                    <span
                      aria-hidden="true"
                      className={cn(
                        "flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                        isActive ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground",
                      )}
                    >
                      {badge}
                    </span>
                  ) : Icon ? (
                    <Icon
                      className={cn("size-4 shrink-0", isActive ? "text-primary" : "text-sidebar-foreground/70")}
                      aria-hidden="true"
                    />
                  ) : (
                    <span className="size-4 shrink-0" aria-hidden="true" />
                  )}
                  <span className="truncate">{label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Panel resolution — section groups OR test/org-scoped overrides ────────────

function usePanel(section) {
  const { pathname } = useLocation()
  const { activeOrg } = useOrg()
  // Called unconditionally (hooks rule); null when not in a class scope.
  const classScope = matchClassScope(pathname)
  const cls = useClass(classScope ? classScope.classId : null)

  const testScope = matchTestScope(pathname)
  if (testScope) {
    const classMatch = pathname.match(/\/classes\/([^/]+)/)
    const classId = classMatch ? classMatch[1] : null
    const items = STAGES
      .map((s) => {
        const to = stageHref({ key: s.key, testId: testScope.testId, classId })
        return to ? { label: s.label, to, badge: STAGES.indexOf(s) + 1, key: s.key } : null
      })
      .filter(Boolean)
      .map((it) => ({ ...it, end: true }))
    return {
      title: "Test",
      back: classId ? { to: `/classes/${classId}`, label: "Back to class" } : null,
      groups: [{ title: "Lifecycle", items }],
      current: testScope.current,
    }
  }

  // Class workspace = the Supabase "project" view: a section sidebar for the class.
  if (classScope) {
    const id = classScope.classId
    const subLabel = pluralize(childKindLabel(activeOrg?.type, cls?.kind_label))
    const items = [
      { label: "Overview", to: `/classes/${id}`, end: true },
      { label: subLabel, to: `/classes/${id}/groups` },
      { label: "Exams", to: `/classes/${id}/exams` },
      { label: "Students", to: `/classes/${id}/students` },
      { label: "Subjects", to: `/classes/${id}/subjects` },
    ]
    if (activeOrg?.role === "admin") {
      items.push({ label: "Teacher access", to: `/classes/${id}/access` })
    }
    items.push({ label: "Settings", to: `/classes/${id}/settings` })
    return {
      title: cls?.name ?? "Class",
      back: { to: "/classes", label: "All classes" },
      groups: [{ title: "Class", items }],
    }
  }

  const orgScope = matchOrgScope(pathname)
  if (orgScope) {
    const role = activeOrg?.role
    const items = [
      { label: "Members", to: `/organizations/${orgScope.orgId}/members`, end: true },
      { label: "Billing", to: `/organizations/${orgScope.orgId}/billing`, end: true },
    ]
    if (role === "admin") {
      items.push({ label: "Roles & permissions", to: `/organizations/${orgScope.orgId}/roles`, end: true })
      items.push({ label: "Audit", to: `/organizations/${orgScope.orgId}/audit`, end: true })
      items.push({ label: "Settings", to: `/organizations/${orgScope.orgId}/settings`, end: true })
    }
    return {
      title: activeOrg?.name ?? "Organization",
      back: { to: "/organizations", label: "All organizations" },
      groups: [{ title: "Organization", items }],
    }
  }

  if (section.groups) {
    return { title: section.label, back: null, groups: section.groups }
  }
  return null
}

// ─── Primary rail (w-14 icon rail + tooltips) ──────────────────────────────────

function RailItem({ section, activeKey }) {
  const Icon = section.icon
  const active = section.key === activeKey
  return (
    <NavLink
      to={section.to}
      aria-label={section.label}
      aria-current={active ? "page" : undefined}
      className={cn(
        "mx-2 flex h-9 items-center gap-2.5 rounded-md px-2 motion-safe-card outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        active
          ? "bg-nav-active-bg text-nav-active-fg"
          : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60",
      )}
    >
      <Icon className="size-5 shrink-0" aria-hidden="true" />
      <span className="whitespace-nowrap text-sm font-medium opacity-0 transition-opacity duration-200 group-hover/rail:opacity-100">
        {section.label}
      </span>
    </NavLink>
  )
}

function PrimaryRail({ activeKey }) {
  return (
    // A w-14 spacer keeps the column in the flex flow; the real rail is fixed and
    // EXPANDS on hover (overlaying content, no reflow) so the icon labels show.
    <div className="hidden w-14 shrink-0 lg:block">
      <aside
        aria-label="Primary"
        className="group/rail fixed inset-y-0 left-0 z-40 flex w-14 flex-col gap-1 overflow-hidden border-r border-strong bg-canvas py-2 transition-[width] duration-200 ease-out hover:w-56 hover:shadow-overlay"
      >
        <Link
          to="/dashboard"
          aria-label="DoxaEd home"
          className="mx-2 mb-1 flex h-9 items-center gap-2.5 rounded-md px-2 text-sm font-bold text-primary"
        >
          <span className="grid size-5 shrink-0 place-items-center">DX</span>
          <span className="whitespace-nowrap opacity-0 transition-opacity duration-200 group-hover/rail:opacity-100">
            DoxaEd OMR
          </span>
        </Link>
        {NAV.filter((s) => !s.footer).map((s) => (
          <RailItem key={s.key} section={s} activeKey={activeKey} />
        ))}
        <div className="mt-auto flex flex-col gap-1">
          {NAV.filter((s) => s.footer).map((s) => (
            <RailItem key={s.key} section={s} activeKey={activeKey} />
          ))}
          <div className="mx-2 flex h-9 items-center px-0.5">
            <ThemeToggle />
          </div>
          <div className="mx-2 flex h-9 items-center px-0.5">
            <AccountMenu compact />
          </div>
        </div>
      </aside>
    </div>
  )
}

// ─── Secondary nav (w-60 contextual panel, collapsible) ────────────────────────

function SecondaryNav({ panel, collapsed, onToggle }) {
  return (
    <aside
      aria-label="Secondary"
      className={cn(
        "hidden shrink-0 flex-col border-r border-strong bg-surface-1 transition-[width] duration-[--dur] lg:flex",
        collapsed ? "w-0 overflow-hidden" : "w-60",
      )}
    >
      <div className="flex h-14 items-center justify-between gap-2 border-b border-border px-4">
        <span className="truncate text-sm font-semibold tracking-tight-1">{panel.title}</span>
        <Button size="icon-sm" variant="ghost" aria-label="Collapse sidebar" onClick={onToggle}>
          <PanelLeftCloseIcon className="size-4" aria-hidden="true" />
        </Button>
      </div>
      {panel.back && (
        <div className="border-b border-border px-2 py-2">
          <Link
            to={panel.back.to}
            className="flex min-h-[40px] items-center gap-2 rounded-md px-2.5 py-2 text-sm text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
          >
            <ArrowLeftIcon className="size-4" aria-hidden="true" />
            {panel.back.label}
          </Link>
        </div>
      )}
      <nav className="flex-1 overflow-y-auto py-2" aria-label="Section navigation">
        {panel.groups.map((g) => (
          <NavSection key={g.title} title={g.title} items={g.items} />
        ))}
      </nav>
      <div className="border-t border-border p-2">
        <OrgSwitcher compact />
      </div>
    </aside>
  )
}

// ─── OrgSwitcher — Popover + Command (type-to-filter) ──────────────────────────

function OrgSwitcher({ compact = false }) {
  const { orgs, activeOrg, setActiveOrg } = useOrg()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const label = activeOrg ? activeOrg.name : "Select organization"

  function handleSwitch(id) {
    setActiveOrg(id)
    setOpen(false)
    navigate("/dashboard")
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          aria-label="Switch organization"
          className={cn(
            "flex min-h-[40px] w-full items-center gap-2 rounded-md border border-border bg-surface-1 px-2.5 py-1.5 text-sm font-medium hover:bg-muted motion-safe-card outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
            compact && "border-sidebar-border bg-sidebar-accent/30 hover:bg-sidebar-accent",
          )}
        >
          <Avatar className="size-5">
            <AvatarFallback className="text-[10px]">{(label?.[0] ?? "P").toUpperCase()}</AvatarFallback>
          </Avatar>
          <span className="min-w-0 flex-1 truncate text-left">{label}</span>
          {activeOrg?.role && (
            <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground capitalize">
              {activeOrg.role}
            </span>
          )}
          <ChevronsUpDownIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-60 p-0">
        <Command>
          <CommandInput placeholder="Find organization…" />
          <CommandList>
            <CommandEmpty>No organizations found.</CommandEmpty>
            <CommandGroup heading="Organizations">
              {orgs.map((org) => (
                <CommandItem key={org.id} value={org.name} onSelect={() => handleSwitch(org.id)}>
                  <Avatar className="size-5">
                    <AvatarFallback className="text-[10px]">
                      {(org.name?.[0] ?? "O").toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="truncate">{org.name}</span>
                  {activeOrg?.id === org.id && (
                    <CheckIcon className="ml-auto size-4" aria-hidden="true" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
          <div className="border-t border-border p-1">
            <button
              onClick={() => {
                setOpen(false)
                navigate("/organizations/new")
              }}
              className="flex w-full min-h-[40px] items-center gap-2 rounded-md px-2 py-2 text-sm text-foreground hover:bg-accent hover:text-accent-foreground"
            >
              <PlusIcon className="size-4 text-muted-foreground" aria-hidden="true" />
              Create organization
            </button>
          </div>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

// ─── Account menu (avatar, pinned top-right) ───────────────────────────────────

function AccountMenu({ compact = false }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className={cn(
          "flex items-center gap-2 rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
          compact
            ? "size-9 justify-center hover:bg-sidebar-accent/60"
            : "min-h-[40px] border border-border bg-surface-1 px-1.5 py-1 hover:bg-muted",
        )}
      >
        <Avatar className="size-7">
          <AvatarFallback>{initials(user)}</AvatarFallback>
        </Avatar>
        {!compact && (
          <span className="hidden min-w-0 flex-col items-start sm:flex">
            <span className="max-w-[140px] truncate text-sm font-medium leading-tight">
              {user?.name || user?.first_name || "Account"}
            </span>
            <span className="max-w-[140px] truncate text-xs leading-tight text-muted-foreground">
              {user?.email}
            </span>
          </span>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="truncate text-sm font-medium text-foreground">
            {user?.name || user?.first_name || "Account"}
          </span>
          {user?.email && (
            <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/profile" className="flex items-center gap-2">
            <UserIcon className="size-4" aria-hidden="true" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={handleLogout} className="gap-2">
          <LogOutIcon className="size-4" aria-hidden="true" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ─── Two-level mobile drawer (reuses Sheet) ────────────────────────────────────

function MobileDrawer() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          aria-label="Open navigation menu"
          className="flex min-h-[40px] min-w-[40px] items-center justify-center rounded-md hover:bg-muted lg:hidden"
        >
          <MenuIcon className="size-5" aria-hidden="true" />
        </button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader>
          <SheetTitle>
            <Link to="/dashboard" onClick={close} className="text-base font-bold tracking-tight">
              DoxaEd OMR
            </Link>
          </SheetTitle>
        </SheetHeader>
        <div className="border-b border-sidebar-border p-2">
          <OrgSwitcher compact />
        </div>
        <nav className="flex-1 overflow-y-auto py-2" aria-label="Mobile navigation">
          <Accordion type="multiple" className="px-1">
            {NAV.map((section) => {
              const Icon = section.icon
              if (!section.groups) {
                return (
                  <NavLink
                    key={section.key}
                    to={section.to}
                    onClick={close}
                    className={({ isActive }) =>
                      cn(
                        "flex min-h-[44px] items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium",
                        isActive
                          ? "bg-nav-active-bg text-nav-active-fg"
                          : "text-sidebar-foreground hover:bg-sidebar-accent/60",
                      )
                    }
                  >
                    <Icon className="size-4 shrink-0" aria-hidden="true" />
                    {section.label}
                  </NavLink>
                )
              }
              return (
                <AccordionItem key={section.key} value={section.key} className="border-b-0">
                  <AccordionTrigger className="min-h-[44px] rounded-md px-3 py-2 text-sm font-medium hover:bg-sidebar-accent/60 hover:no-underline">
                    <span className="flex items-center gap-2.5">
                      <Icon className="size-4 shrink-0" aria-hidden="true" />
                      {section.label}
                    </span>
                  </AccordionTrigger>
                  <AccordionContent className="pb-1 pl-3">
                    {section.groups.map((g) => (
                      <NavSection key={g.title} items={g.items} onNavigate={close} />
                    ))}
                  </AccordionContent>
                </AccordionItem>
              )
            })}
          </Accordion>
        </nav>
      </SheetContent>
    </Sheet>
  )
}

// ─── Bottom tab bar (mobile) ───────────────────────────────────────────────────

function BottomTabBar() {
  return (
    <nav
      aria-label="Bottom navigation"
      className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-background lg:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      {BOTTOM_TABS.map(({ label, to, icon: Icon }) => (
        <NavLink
          key={to + label}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium motion-safe-card",
              isActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon className={cn("size-5 shrink-0", isActive && "text-primary")} aria-hidden="true" />
              <span>{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

// ─── Top bar ───────────────────────────────────────────────────────────────────

function TopBar({ section, panelCollapsed, hasPanel, onExpandPanel }) {
  const { activeOrg } = useOrg()
  const [scrolled, setScrolled] = useState(false)
  const crumbs = useBreadcrumbItems(section, { orgName: activeOrg?.name })

  useEffect(() => {
    const main = document.getElementById("main")
    if (!main) return
    const onScroll = () => setScrolled(main.scrollTop > 4)
    main.addEventListener("scroll", onScroll, { passive: true })
    return () => main.removeEventListener("scroll", onScroll)
  }, [])

  function openCmdK() {
    window.dispatchEvent(new Event("cmdk:open"))
  }

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex min-h-[56px] items-center gap-2 bg-background/85 px-3 backdrop-blur-sm supports-backdrop-filter:bg-background/70 sm:px-4",
        scrolled && "border-b border-border",
      )}
    >
      <MobileDrawer />
      <Link to="/dashboard" className="mr-1 text-sm font-bold tracking-tight lg:hidden">
        DoxaEd OMR
      </Link>

      {hasPanel && panelCollapsed && (
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label="Open sidebar"
          className="hidden lg:inline-flex"
          onClick={onExpandPanel}
        >
          <PanelLeftOpenIcon className="size-4" aria-hidden="true" />
        </Button>
      )}

      <Breadcrumb items={crumbs} className="hidden min-w-0 flex-1 sm:flex" />
      <div className="flex-1 sm:hidden" />

      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={openCmdK}
          aria-label="Open command menu"
          className="hidden h-8 items-center gap-2 rounded-md border border-border bg-surface-1 px-2.5 text-sm text-muted-foreground hover:bg-muted md:flex"
        >
          <SearchIcon className="size-3.5" aria-hidden="true" />
          <span>Search…</span>
          <kbd className="rounded border border-border bg-muted px-1.5 text-[10px]">⌘K</kbd>
        </button>
        <button
          onClick={openCmdK}
          aria-label="Open command menu"
          className="flex size-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted md:hidden"
        >
          <SearchIcon className="size-4" aria-hidden="true" />
        </button>
        <OrgSwitcherTopBar />
        <AccountMenu />
      </div>
    </header>
  )
}

// A bounded-width wrapper so the OrgSwitcher reads well in the top bar.
function OrgSwitcherTopBar() {
  return (
    <div className="hidden w-44 sm:block">
      <OrgSwitcher />
    </div>
  )
}

// ─── AppShell — root layout for authenticated pages ────────────────────────────

/**
 * AppShell v2 — two-level shell: primary icon rail (w-14) + contextual secondary
 * panel (w-60, route-driven & collapsible) + top bar (breadcrumb, Cmd-K, org
 * switcher, account, theme). Childless sections (Home) hide the panel and the
 * main column goes full-width. Cmd-K is mounted once here.
 *
 * Props:
 *   children — page content (rendered unchanged inside the shell)
 *   isAdmin  — accepted for back-compat with the route wrapper (no longer used:
 *              admin-only panel items are derived from the active org's role).
 */
export default function AppShell({ children }) {
  const section = useActiveSection()
  const panel = usePanel(section)
  const hasPanel = !!panel

  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(PANEL_COLLAPSE_KEY) === "1"
    } catch {
      return false
    }
  })

  function toggleCollapsed() {
    setCollapsed((c) => {
      const next = !c
      try {
        localStorage.setItem(PANEL_COLLAPSE_KEY, next ? "1" : "0")
      } catch {
        /* ignore */
      }
      return next
    })
  }

  return (
    <div className="app-density flex min-h-screen bg-canvas text-foreground">
      <PrimaryRail activeKey={section.key} />
      {hasPanel && (
        <SecondaryNav panel={panel} collapsed={collapsed} onToggle={toggleCollapsed} />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          section={section}
          hasPanel={hasPanel}
          panelCollapsed={collapsed}
          onExpandPanel={toggleCollapsed}
        />
        <main id="main" className="flex-1 overflow-auto pb-16 lg:pb-0">
          {children}
        </main>
        <BottomTabBar />
      </div>
      <CommandMenu />
    </div>
  )
}
