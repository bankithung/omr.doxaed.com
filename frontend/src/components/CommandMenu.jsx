import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTheme } from "next-themes"
import {
  BuildingIcon,
  PlusIcon,
  ScanLineIcon,
  SunMoonIcon,
  ClockIcon,
} from "lucide-react"

import { useOrg } from "@/org/OrgContext"
import { flattenNavLeaves } from "@/components/shell/nav-config"
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/ui/command"

const MRU_KEY = "cmdk.recent"
const MRU_MAX = 5

function readMru() {
  try {
    const raw = localStorage.getItem(MRU_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.slice(0, MRU_MAX) : []
  } catch {
    return []
  }
}

function pushMru(entry) {
  try {
    const list = readMru().filter((e) => e.to !== entry.to)
    list.unshift(entry)
    localStorage.setItem(MRU_KEY, JSON.stringify(list.slice(0, MRU_MAX)))
  } catch {
    /* ignore quota / serialization errors — MRU is best-effort */
  }
}

/**
 * CommandMenu — global ⌘K / Ctrl-K command palette. Mounted ONCE in AppShell.
 * Groups: Go to (NAV leaves), Organizations (switch active org), Actions,
 * and Recent (localStorage MRU of visited destinations).
 */
export default function CommandMenu() {
  const [open, setOpen] = useState(false)
  const [recent, setRecent] = useState([])
  const navigate = useNavigate()
  const { orgs, activeOrg, setActiveOrg } = useOrg()
  const { resolvedTheme, setTheme } = useTheme()

  // Global ⌘K / Ctrl-K toggle.
  useEffect(() => {
    function onKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [])

  // Allow the TopBar trigger to open the palette via a window event.
  useEffect(() => {
    function onOpen() {
      setOpen(true)
    }
    window.addEventListener("cmdk:open", onOpen)
    return () => window.removeEventListener("cmdk:open", onOpen)
  }, [])

  // Refresh the recent list whenever the palette opens.
  useEffect(() => {
    if (open) setRecent(readMru())
  }, [open])

  const go = useCallback(
    (to, label) => {
      setOpen(false)
      pushMru({ to, label })
      navigate(to)
    },
    [navigate]
  )

  const navLeaves = flattenNavLeaves()

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search or jump to…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Go to">
          {navLeaves.map((item) => {
            const Icon = item.icon
            return (
              <CommandItem
                key={item.to}
                value={`goto ${item.label}`}
                onSelect={() => go(item.to, item.label)}
              >
                {Icon ? <Icon aria-hidden="true" /> : null}
                {item.label}
              </CommandItem>
            )
          })}
        </CommandGroup>

        {orgs.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Organizations">
              {orgs.map((org) => (
                <CommandItem
                  key={org.id}
                  value={`org ${org.name}`}
                  onSelect={() => {
                    setOpen(false)
                    setActiveOrg(org.id)
                    navigate("/dashboard")
                  }}
                >
                  <BuildingIcon aria-hidden="true" />
                  {org.name}
                  {activeOrg?.id === org.id && (
                    <span className="ml-auto text-xs text-muted-foreground">Active</span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        <CommandSeparator />
        <CommandGroup heading="Actions">
          <CommandItem value="action new class" onSelect={() => go("/classes", "Classes")}>
            <PlusIcon aria-hidden="true" />
            New class
          </CommandItem>
          <CommandItem value="action new roster" onSelect={() => go("/rosters", "Rosters")}>
            <PlusIcon aria-hidden="true" />
            New roster
          </CommandItem>
          <CommandItem value="action scan" onSelect={() => go("/scan", "Scan")}>
            <ScanLineIcon aria-hidden="true" />
            Scan sheets
          </CommandItem>
          <CommandItem
            value="action toggle theme"
            onSelect={() => {
              setTheme(resolvedTheme === "dark" ? "light" : "dark")
              setOpen(false)
            }}
          >
            <SunMoonIcon aria-hidden="true" />
            Toggle theme
          </CommandItem>
        </CommandGroup>

        {recent.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Recent">
              {recent.map((item) => (
                <CommandItem
                  key={item.to}
                  value={`recent ${item.label}`}
                  onSelect={() => go(item.to, item.label)}
                >
                  <ClockIcon aria-hidden="true" />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>

      <div className="flex items-center gap-3 border-t border-border px-3 py-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px]">↑↓</kbd>
          navigate
        </span>
        <span className="flex items-center gap-1">
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px]">↵</kbd>
          open
        </span>
        <span className="flex items-center gap-1">
          <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px]">esc</kbd>
          close
        </span>
      </div>
    </CommandDialog>
  )
}
