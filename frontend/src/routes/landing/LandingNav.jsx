import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

/**
 * DoxaEd OMR wordmark — a clean, text-only typographic lockup (brand name +
 * refined OMR accent eyebrow). No logo glyph — the wordmark alone carries it.
 * Flat, app-token-driven.
 */
function Wordmark() {
  return (
    <Link
      to="/"
      className="flex items-baseline gap-1.5 text-foreground"
      aria-label="DoxaEd OMR — home"
    >
      <span className="text-[1.05rem] font-semibold tracking-tight">DoxaEd</span>
      <span className="font-mono text-[11px] font-medium uppercase tracking-[0.28em] text-primary">OMR</span>
    </Link>
  )
}

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Built for", href: "#use-cases" },
  { label: "Why", href: "#why" },
]

/**
 * LandingNav — sticky, translucent + backdrop-blur header with a hairline bottom
 * border (the Supabase nav). Ghost links collapse on mobile; the "Get started"
 * CTA + "Sign in" stay. h-16 (64px) bar. All flat, app tokens, theme-aware.
 */
export default function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[90rem] items-center justify-between px-6 lg:px-16 xl:px-20">
        <Wordmark />

        <nav className="hidden items-center gap-7 text-sm sm:flex" aria-label="Primary">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild className="hidden h-9 px-3 sm:inline-flex">
            <Link to="/login">Sign in</Link>
          </Button>
          <Button size="sm" asChild className="h-9 px-3.5">
            <Link to="/register">Get started</Link>
          </Button>
        </div>
      </div>
    </header>
  )
}
