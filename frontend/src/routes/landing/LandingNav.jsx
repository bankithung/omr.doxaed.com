import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

/**
 * DoxaEd OMR wordmark — premium two-part lockup (brand name + OMR eyebrow) on a
 * small brand glyph. Flat, app-token-driven.
 */
function Wordmark() {
  return (
    <Link
      to="/"
      className="flex items-center gap-2 text-foreground"
      aria-label="DoxaEd OMR — home"
    >
      <span className="flex size-7 items-center justify-center rounded-md bg-primary">
        <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
          {[6, 12, 18].map((cy) => (
            <circle key={cy} cx="8" cy={cy} r="2.4" fill="none" stroke="var(--color-primary-foreground)" strokeWidth="1.6" />
          ))}
          <circle cx="16" cy="12" r="2.4" fill="var(--color-primary-foreground)" />
        </svg>
      </span>
      <span className="flex items-baseline gap-1.5">
        <span className="font-semibold tracking-tight">DoxaEd</span>
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.28em] text-primary">OMR</span>
      </span>
    </Link>
  )
}

const NAV_LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Features", href: "#features" },
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
