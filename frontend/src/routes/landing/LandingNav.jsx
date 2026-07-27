import { useState } from "react"
import { Link } from "react-router-dom"
import { Menu, X } from "lucide-react"
import { Button } from "@/components/ui/button"

/**
 * DoxaEd OMR wordmark — a clean, text-only typographic lockup (brand name +
 * refined OMR accent eyebrow). No logo glyph — the wordmark alone carries it.
 * Flat, app-token-driven.
 */
function Wordmark({ onClick }) {
  return (
    <Link
      to="/"
      onClick={onClick}
      className="flex items-baseline gap-1.5 text-foreground"
      aria-label="DoxaEd OMR, home"
    >
      <span className="text-[1.05rem] font-semibold tracking-tight">DoxaEd</span>
      <span className="font-mono text-[11px] font-medium uppercase tracking-[0.28em] text-indigo">OMR</span>
    </Link>
  )
}

// Real destinations: standalone pages get router links; the landing's own
// sections are reached via root-anchored hrefs (`/#anchor`) so they work from
// any page, not just "/".
const NAV_LINKS = [
  { label: "Features", to: "/features" },
  { label: "Pricing", to: "/pricing" },
  { label: "How it works", to: "/how-it-works" },
  { label: "Built for", to: "/built-for" },
  { label: "About", to: "/about" },
]

function NavLink({ link, onClick, className }) {
  return link.to ? (
    <Link key={link.to} to={link.to} onClick={onClick} className={className}>
      {link.label}
    </Link>
  ) : (
    <a key={link.href} href={link.href} onClick={onClick} className={className}>
      {link.label}
    </a>
  )
}

/**
 * LandingNav — sticky, translucent + backdrop-blur header with a hairline bottom
 * border (the Supabase nav). On md+ the ghost nav links + Sign in / Get started
 * show inline; below md they collapse into a hamburger that opens a full mobile
 * menu (links + auth actions). h-16 (64px) bar. Flat, app tokens, theme-aware.
 *
 * Shared across the landing + every standalone public page (via PublicLayout,
 * AuthLayout, LegalLayout).
 */
export default function LandingNav() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[90rem] items-center justify-between px-6 lg:px-16 xl:px-20">
        <Wordmark onClick={close} />

        {/* Desktop nav */}
        <nav className="hidden items-center gap-7 text-sm md:flex" aria-label="Primary">
          {NAV_LINKS.map((l) => (
            <NavLink
              key={l.label}
              link={l}
              className="text-muted-foreground transition-colors hover:text-foreground"
            />
          ))}
        </nav>

        {/* Desktop auth */}
        <div className="hidden items-center gap-2 md:flex">
          <Button variant="ghost" size="sm" asChild className="h-9 px-3">
            <Link to="/login">Sign in</Link>
          </Button>
          <Button size="sm" asChild className="h-9 px-3.5">
            <Link to="/register">Get started</Link>
          </Button>
        </div>

        {/* Mobile: primary CTA + hamburger */}
        <div className="flex items-center gap-2 md:hidden">
          <Button size="sm" asChild className="h-9 px-3.5">
            <Link to="/register" onClick={close}>Get started</Link>
          </Button>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="flex size-10 items-center justify-center rounded-md border border-border text-foreground transition-colors hover:bg-surface-2"
          >
            {open ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Mobile menu panel */}
      {open ? (
        <div className="border-t border-border bg-background md:hidden">
          <nav className="mx-auto flex max-w-[90rem] flex-col px-4 py-3" aria-label="Mobile">
            {NAV_LINKS.map((l) => (
              <NavLink
                key={l.label}
                link={l}
                onClick={close}
                className="rounded-md px-3 py-3 text-sm text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
              />
            ))}
            <div className="mt-2 flex flex-col gap-2 border-t border-border pt-3">
              <Button variant="outline" asChild className="h-11 w-full">
                <Link to="/login" onClick={close}>Sign in</Link>
              </Button>
              <Button asChild className="h-11 w-full">
                <Link to="/register" onClick={close}>Get started</Link>
              </Button>
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  )
}
