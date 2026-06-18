import { Link } from "react-router-dom"
import { BarChart3, ScanLine, ShieldCheck } from "lucide-react"

// Wordmark shared by the branded aside and the mobile header. Uses only the
// flat app design tokens (no marketing-page theme).
function Wordmark({ className = "" }) {
  return (
    <Link
      to="/"
      className={`inline-flex items-baseline gap-1.5 font-bold tracking-tight ${className}`}
      aria-label="DoxaEd OMR — home"
    >
      <span className="text-foreground">DoxaEd</span>
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
        OMR
      </span>
    </Link>
  )
}

const FEATURES = [
  { icon: ScanLine, title: "Scan & auto-grade", desc: "Upload sheets from any phone or scanner." },
  { icon: BarChart3, title: "Instant analytics", desc: "Item analysis and report cards per test." },
  { icon: ShieldCheck, title: "Private by design", desc: "Encrypted student data, owner-scoped." },
]

function FeatureList() {
  return (
    <ul className="space-y-5">
      {FEATURES.map(({ icon: Icon, title, desc }) => (
        <li key={title} className="flex gap-3">
          <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background text-primary">
            <Icon className="size-4" aria-hidden="true" />
          </span>
          <div className="space-y-0.5">
            <p className="text-sm font-medium text-sidebar-foreground">{title}</p>
            <p className="text-sm text-muted-foreground">{desc}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}

/**
 * Branded split auth layout (spec §5). Left: a branded aside (hidden on mobile);
 * right: a centered max-w-sm form column. Flat, dark-mode correct, app tokens.
 */
export default function AuthLayout({ title, subtitle, children, footer, aside }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      {/* Branded aside — desktop only */}
      <aside className="relative hidden flex-col justify-between border-r border-border bg-sidebar p-10 lg:flex">
        <Wordmark className="text-lg" />
        <div className="max-w-sm space-y-8">
          <div className="space-y-2">
            <h2 className="text-xl font-semibold tracking-tight text-sidebar-foreground">
              OMR exams, graded in minutes.
            </h2>
            <p className="text-sm text-muted-foreground">
              Generate shuffled answer sheets, scan them back in, and get auditable
              results with full analytics.
            </p>
          </div>
          {aside ?? <FeatureList />}
        </div>
        <p className="text-xs text-muted-foreground">© DoxaEd</p>
      </aside>

      {/* Form column */}
      <main className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm space-y-6">
          <Wordmark className="text-lg lg:hidden" />
          <div className="space-y-1.5">
            {title ? (
              <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            ) : null}
            {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
          </div>
          {children}
          {footer}
        </div>
      </main>
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
