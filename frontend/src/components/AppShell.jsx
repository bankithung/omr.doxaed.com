import { useState } from "react"
import { Link, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"
import { useOrg } from "@/org/OrgContext"
import { cn } from "@/lib/utils"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  LayoutDashboardIcon,
  UsersIcon,
  ScanLineIcon,
  BarChart2Icon,
  BuildingIcon,
  UserCogIcon,
  ReceiptIcon,
  ShieldIcon,
  MenuIcon,
  ChevronDownIcon,
  UserIcon,
  LogOutIcon,
  HomeIcon,
  FileTextIcon,
} from "lucide-react"

// ─── Nav item definitions ─────────────────────────────────────────────────────

const WORKSPACE_NAV = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboardIcon },
  { label: "Classes", to: "/classes", icon: FileTextIcon },
  { label: "Rosters", to: "/rosters", icon: UsersIcon },
]

const RUN_NAV = [
  { label: "Scan", to: "/scan", icon: ScanLineIcon },
  { label: "Results", to: "/tests", icon: BarChart2Icon },
]

const ORG_NAV = [
  { label: "Organizations", to: "/organizations", icon: BuildingIcon },
]

// Admin-only org nav items (shown when active member is admin)
const ORG_ADMIN_NAV = [
  { label: "Members", to: "/organizations", icon: UserCogIcon },
  { label: "Audit", to: "/organizations", icon: ShieldIcon },
  { label: "Billing", to: "/organizations", icon: ReceiptIcon },
]

// Bottom tab bar items for mobile
const BOTTOM_TABS = [
  { label: "Home", to: "/dashboard", icon: HomeIcon },
  { label: "Classes", to: "/classes", icon: FileTextIcon },
  { label: "Scan", to: "/scan", icon: ScanLineIcon },
  { label: "Results", to: "/tests", icon: BarChart2Icon },
]

// ─── Helpers ─────────────────────────────────────────────────────────────────

function NavSection({ title, items, onNavigate }) {
  return (
    <div className="px-2 py-1">
      <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-widest text-sidebar-foreground/50 select-none">
        {title}
      </p>
      <ul className="space-y-0.5">
        {items.map(({ label, to, icon: Icon }) => (
          <li key={to + label}>
            <NavLink
              to={to}
              aria-current={undefined}
              className={({ isActive }) =>
                cn(
                  "flex min-h-[40px] items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                )
              }
              onClick={onNavigate}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cn(
                      "size-4 shrink-0",
                      isActive ? "text-sidebar-primary" : "text-sidebar-foreground/70",
                    )}
                    aria-hidden="true"
                  />
                  {label}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── OrgSwitcher — reload-free ─────────────────────────────────────────────────
// api/client.js reads activeOrg from localStorage at request-time (inside the
// interceptor function body, not at module load), so updating localStorage via
// setActiveOrg() is sufficient for the NEXT request to carry the right header.
// After switching we navigate to /dashboard to trigger a fresh data fetch for
// the new context without a full window.location.reload().

function OrgSwitcher({ compact = false }) {
  const { orgs, activeOrg, setActiveOrg } = useOrg()
  const navigate = useNavigate()
  const label = activeOrg ? activeOrg.name : "Personal"

  function handleSwitch(id) {
    setActiveOrg(id)
    // Navigate to dashboard to re-fetch data in the new org context.
    // Using navigate() keeps the React tree alive — no full reload.
    navigate("/dashboard")
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm font-medium hover:bg-muted transition-colors min-h-[40px]",
          compact && "border-sidebar-border bg-sidebar-accent/40 hover:bg-sidebar-accent",
        )}
      >
        <BuildingIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="max-w-[120px] truncate">{label}</span>
        <ChevronDownIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuLabel>Workspace</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() => handleSwitch(null)}
          data-active={!activeOrg ? "" : undefined}
          className="data-[active]:font-semibold"
        >
          Personal
        </DropdownMenuItem>
        {orgs.length > 0 && <DropdownMenuSeparator />}
        {orgs.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onSelect={() => handleSwitch(org.id)}
            data-active={activeOrg?.id === org.id ? "" : undefined}
            className="data-[active]:font-semibold"
          >
            {org.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ─── Account menu ─────────────────────────────────────────────────────────────

function AccountMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex min-h-[40px] items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm font-medium hover:bg-muted transition-colors">
        <UserIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="hidden max-w-[140px] truncate sm:block">{user?.email ?? "Account"}</span>
        <ChevronDownIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Account</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/profile" className="flex items-center gap-2">
            <UserIcon className="size-4" aria-hidden="true" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={handleLogout}
          className="flex items-center gap-2 text-destructive focus:text-destructive"
        >
          <LogOutIcon className="size-4" aria-hidden="true" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ─── Sidebar nav content (shared between desktop sidebar + mobile drawer) ─────

function SidebarNav({ onNavigate, isAdmin }) {
  return (
    <nav className="flex flex-col gap-1 overflow-y-auto py-2" aria-label="Main navigation">
      <NavSection title="Workspace" items={WORKSPACE_NAV} onNavigate={onNavigate} />
      <NavSection title="Run" items={RUN_NAV} onNavigate={onNavigate} />
      <NavSection
        title="Org"
        items={isAdmin ? [...ORG_NAV, ...ORG_ADMIN_NAV] : ORG_NAV}
        onNavigate={onNavigate}
      />
    </nav>
  )
}

// ─── Desktop sidebar ──────────────────────────────────────────────────────────

function DesktopSidebar({ isAdmin }) {
  return (
    <aside
      className="hidden lg:flex lg:flex-col w-56 shrink-0 border-r border-sidebar-border bg-sidebar"
      aria-label="Sidebar"
    >
      {/* Brand */}
      <div className="flex items-center gap-2 border-b border-sidebar-border px-4 py-3">
        <Link
          to="/"
          className="text-base font-bold tracking-tight text-sidebar-foreground hover:text-sidebar-primary transition-colors"
        >
          OMRFlow
        </Link>
      </div>

      {/* Org switcher in sidebar */}
      <div className="border-b border-sidebar-border px-3 py-3">
        <OrgSwitcher compact />
      </div>

      {/* Nav */}
      <SidebarNav isAdmin={isAdmin} />
    </aside>
  )
}

// ─── Mobile drawer ────────────────────────────────────────────────────────────

function MobileDrawer({ isAdmin }) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          className="flex min-h-[40px] min-w-[40px] items-center justify-center rounded-md hover:bg-muted transition-colors lg:hidden"
          aria-label="Open navigation menu"
        >
          <MenuIcon className="size-5" aria-hidden="true" />
        </button>
      </SheetTrigger>
      <SheetContent side="left">
        <SheetHeader>
          <SheetTitle>
            <Link
              to="/"
              className="text-base font-bold tracking-tight text-sidebar-foreground hover:text-sidebar-primary transition-colors"
              onClick={() => setOpen(false)}
            >
              OMRFlow
            </Link>
          </SheetTitle>
        </SheetHeader>

        {/* Org switcher in drawer */}
        <div className="border-b border-sidebar-border px-3 py-3">
          <OrgSwitcher compact />
        </div>

        <SidebarNav onNavigate={() => setOpen(false)} isAdmin={isAdmin} />
      </SheetContent>
    </Sheet>
  )
}

// ─── Top bar ──────────────────────────────────────────────────────────────────

function TopBar({ isAdmin, breadcrumb }) {
  return (
    <header className="sticky top-0 z-40 flex min-h-[56px] items-center gap-2 border-b border-border bg-background px-3 sm:px-4">
      {/* Hamburger (mobile only) */}
      <MobileDrawer isAdmin={isAdmin} />

      {/* Brand (mobile only — desktop has it in sidebar) */}
      <Link
        to="/"
        className="mr-1 text-sm font-bold tracking-tight hover:text-primary transition-colors lg:hidden"
      >
        OMRFlow
      </Link>

      {/* Breadcrumb slot */}
      {breadcrumb && (
        <div className="hidden sm:block flex-1 min-w-0 truncate text-sm text-muted-foreground">
          {breadcrumb}
        </div>
      )}
      {!breadcrumb && <div className="flex-1" />}

      {/* Right controls */}
      <div className="ml-auto flex items-center gap-2">
        {/* Org switcher on top bar (≥lg replaces drawer switcher visually — but
            we keep the sidebar one too so there's never 0 switchers visible) */}
        <div className="hidden sm:block lg:hidden">
          <OrgSwitcher />
        </div>
        <AccountMenu />
      </div>
    </header>
  )
}

// ─── Mobile bottom tab bar ────────────────────────────────────────────────────

function BottomTabBar() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-border bg-background lg:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      aria-label="Bottom navigation"
    >
      {BOTTOM_TABS.map(({ label, to, icon: Icon }) => (
        <NavLink
          key={to + label}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium transition-colors min-h-[56px]",
              isActive
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                className={cn("size-5 shrink-0", isActive && "text-primary")}
                aria-hidden="true"
              />
              <span>{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

// ─── AppShell — root layout for authenticated pages ───────────────────────────

/**
 * AppShell wraps all authenticated routes.
 * Props:
 *   children   — page content
 *   breadcrumb — optional ReactNode shown in the top bar breadcrumb slot
 *   isAdmin    — whether the active user is an org admin (controls admin-only nav items)
 */
export default function AppShell({ children, breadcrumb, isAdmin = false }) {
  return (
    <div className="flex min-h-screen">
      {/* Desktop left sidebar */}
      <DesktopSidebar isAdmin={isAdmin} />

      {/* Right column: top bar + content */}
      <div className="flex flex-1 flex-col min-w-0">
        <TopBar isAdmin={isAdmin} breadcrumb={breadcrumb} />

        {/* Page content — bottom padding on mobile to clear the tab bar */}
        <main id="main" className="flex-1 overflow-auto pb-16 lg:pb-0">
          {children}
        </main>

        {/* Mobile bottom tab bar */}
        <BottomTabBar />
      </div>
    </div>
  )
}
