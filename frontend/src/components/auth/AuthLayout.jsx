import { Link } from "react-router-dom"
import { Check } from "lucide-react"

import LandingNav from "@/routes/landing/LandingNav"

/**
 * Faint OMR-bubble texture behind the auth card — flat open circles (the
 * product's own motif) on a grid, pooled into a soft area around the card with
 * an ALPHA mask (no colored gradient). Decorative + aria-hidden; gives the
 * centered layout premium depth without splitting it.
 */
function BubbleField() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10"
      style={{
        WebkitMaskImage: "radial-gradient(460px 460px at 50% 42%, #000 0%, transparent 70%)",
        maskImage: "radial-gradient(460px 460px at 50% 42%, #000 0%, transparent 70%)",
      }}
    >
      <svg className="h-full w-full opacity-70" aria-hidden="true">
        <defs>
          <pattern id="auth-omr-bubbles" width="27" height="27" patternUnits="userSpaceOnUse">
            <circle
              cx="13.5"
              cy="13.5"
              r="2.4"
              fill="none"
              stroke="var(--color-border-stronger)"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#auth-omr-bubbles)" />
      </svg>
    </div>
  )
}

// Honest product guarantees shown under the card — real platform behaviour, NOT
// fabricated social proof (no fake logos/counts/testimonials).
const TRUST = ["Server-side grading", "Encrypted student data", "Owner-scoped & auditable"]

/**
 * Centered, premium auth layout. The SAME sticky home-page header (LandingNav)
 * sits on top; below it a single centered max-w-[400px] column on the dark
 * gunmetal `bg-background`: heading + subtitle, the form on a flat `rounded-2xl
 * border bg-card` card (with a subtle top highlight) over a faint brand radial +
 * OMR-bubble texture, then an honest trust row and the legal footer. Flat,
 * theme-aware, app tokens — never split. Used by Login / Register / Forgot /
 * Reset / VerifyEmail / AcceptInvite.
 *
 * Frozen E2E names live in the page content (title/heading props), not here:
 * restyling never touches them.
 */
export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-background">
      {/* The exact same sticky header as the home page, shared site-wide. */}
      <LandingNav />

      <div className="relative flex flex-1 flex-col items-center justify-center px-4 py-12 sm:py-16">
        {/* Faint brand radial — the single allowed subtle glow. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[460px]"
          style={{
            background:
              "radial-gradient(50% 60% at 50% 0%, color-mix(in oklch, var(--color-primary) 11%, transparent), transparent 72%)",
          }}
        />
        {/* Faint OMR-bubble texture pooled behind the card. */}
        <BubbleField />

        <div className="w-full max-w-[400px]">
          <div className="space-y-2 text-center">
            {title ? (
              <h1 className="text-[1.75rem] font-semibold leading-tight tracking-tight text-foreground">
                {title}
              </h1>
            ) : null}
            {subtitle ? <p className="text-[0.95rem] text-muted-foreground">{subtitle}</p> : null}
          </div>

          {/* Card — flat, with a subtle 1px top highlight for premium depth. */}
          <div className="relative mt-7 rounded-2xl border border-border bg-card p-6 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] sm:p-7">
            <div className="space-y-5">{children}</div>
          </div>

          {/* Honest trust row — real guarantees, no fabricated social proof. */}
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5">
            {TRUST.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground"
              >
                <Check className="size-3 text-primary" aria-hidden="true" />
                {t}
              </span>
            ))}
          </div>

          {footer ? <div className="mt-4">{footer}</div> : null}
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
