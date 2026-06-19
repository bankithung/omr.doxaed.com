import { Link } from "react-router-dom"

import LandingNav from "@/routes/landing/LandingNav"

/**
 * Centered Supabase-style auth layout (spec §5). The SAME sticky home-page header
 * (LandingNav) sits on top, then a single centered max-w-sm column on the dark
 * gunmetal `bg-background`: the heading + subtitle, the form on a flat
 * `rounded-xl border bg-card p-6` panel, then the footer. A faint brand radial
 * sits behind the card (the one allowed subtle glow). Flat, theme-aware, app
 * tokens. Used by Login / Register / Forgot / Reset / VerifyEmail / AcceptInvite.
 *
 * Frozen E2E names live in the page content (title/heading props), not here:
 * restyling never touches them.
 */
export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-background">
      {/* The exact same sticky header as the home page, shared site-wide. */}
      <LandingNav />

      <div className="relative flex flex-1 flex-col items-center justify-center px-4 py-12">
        {/* Faint brand radial behind the card — the single allowed subtle glow. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px]"
          style={{
            background:
              "radial-gradient(50% 60% at 50% 0%, color-mix(in oklch, var(--color-primary) 10%, transparent), transparent 72%)",
          }}
        />

        <div className="w-full max-w-sm space-y-6">
          <div className="space-y-1.5 text-center">
            {title ? (
              <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
            ) : null}
            {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
          </div>

          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">{children}</div>

          {footer}
        </div>
      </div>
    </div>
  )
}

// Shared legal footer note for the auth pages. Links to the public Terms /
// Privacy pages.
export function LegalFooter() {
  return (
    <p className="text-center text-xs leading-relaxed text-muted-foreground">
      By continuing you agree to our{" "}
      <Link to="/terms" className="text-primary underline-offset-4 hover:underline">
        Terms
      </Link>{" "}
      and{" "}
      <Link to="/privacy" className="text-primary underline-offset-4 hover:underline">
        Privacy Policy
      </Link>
      .
    </p>
  )
}
