import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import MaterialIcon from "./MaterialIcon"
import { Reveal, RevealItem } from "./motion/reveal"

// ── Real content only — no invented pages, no fake social, no fake newsletter ──
// Anchors are root-anchored (`/#…`) so they resolve from any public page.
const PRODUCT_LINKS = [
  { label: "Features", to: "/features" },
  { label: "Pricing", to: "/pricing" },
  { label: "How it works", to: "/#how-it-works", anchor: true },
  { label: "About", to: "/about" },
  { label: "Contact", to: "/contact" },
  { label: "Sign in", to: "/login" },
  { label: "Create account", to: "/register" },
]

// Resources / trust pages — real, navigable destinations.
const RESOURCE_LINKS = [
  { label: "Getting started", to: "/help" },
  { label: "FAQ", to: "/faq" },
  { label: "Security", to: "/security" },
  { label: "Terms", to: "/terms" },
  { label: "Privacy", to: "/privacy" },
]

const OMR_MODES = [
  "Standard MCQ",
  "Roster pre-bubbled roll (auto-identify)",
  "Competitive / sectional (NEET · UPSC style)",
  "Per-student shuffle",
  "4 or 5 options",
]

const CAPABILITIES = [
  "Batch sheet generation",
  "Shuffled question papers",
  "Scan & auto-grade",
  "Inline scan correction",
  "Review queue (never guessed)",
  "Configurable multi-mark rules",
  "Analytics & item analysis",
  "Two-page report cards",
  "Public result portal",
  "Folders & sharing",
  "Organisations & roles",
]

const TRUST_POINTS = [
  "Server-side grading",
  "Auditable results",
  "Encrypted student PII",
  "Per-organisation data isolation",
  "Works with any phone or scanner",
]

function ColHeading({ children }) {
  return (
    <p className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">{children}</p>
  )
}

// Plain capability/mode entry — routes to the Features page (a real destination).
function FeatureItem({ children }) {
  return (
    <li>
      <Link to="/features" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
        {children}
      </Link>
    </li>
  )
}

function FooterLink({ to, anchor, children }) {
  const cls = "text-sm text-muted-foreground transition-colors hover:text-foreground"
  return anchor ? <a href={to} className={cls}>{children}</a> : <Link to={to} className={cls}>{children}</Link>
}

/**
 * Footer — the real DoxaEd OMR sitemap (Product / OMR modes / Capabilities /
 * Why / Get in touch) with real mailto + doxaed.com + Terms/Privacy links.
 * Restyled flat onto app tokens (theme-aware) with a fadeInUp staggered reveal
 * of the columns. No gradients, no cinematic classes.
 */
export default function Footer() {
  return (
    <footer className="border-t border-border px-6 pb-10 pt-16 lg:px-16 xl:px-20">
      <Reveal className="mx-auto max-w-[90rem]">
        <div className="grid gap-x-8 gap-y-10 lg:grid-cols-[1.6fr_1fr_1fr_1.3fr_1.3fr_1fr_1fr]">
          {/* brand block */}
          <RevealItem className="max-w-sm lg:pr-6">
            <Link to="/" className="flex items-baseline gap-1.5 text-foreground" aria-label="DoxaEd OMR — home">
              <span className="text-[1.05rem] font-semibold tracking-tight">DoxaEd</span>
              <span className="font-mono text-[11px] font-medium uppercase tracking-[0.28em] text-primary">OMR</span>
            </Link>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Shuffled OMR sheets, scanned and auto-graded — every test a full analytics profile.
            </p>
            <Button asChild className="mt-5 h-10 px-4 text-sm">
              <Link to="/register">Start free</Link>
            </Button>
            <p className="mt-5 font-mono text-[11px] text-muted-foreground">DoxaEd OMR · omr.doxaed.com</p>
          </RevealItem>

          {/* product column */}
          <RevealItem as="nav" aria-label="Product" className="lg:border-l lg:border-border lg:pl-6">
            <ColHeading>Product</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {PRODUCT_LINKS.map((l) => (
                <li key={l.label}>
                  <FooterLink to={l.to} anchor={l.anchor}>{l.label}</FooterLink>
                </li>
              ))}
            </ul>
          </RevealItem>

          {/* resources column */}
          <RevealItem as="nav" aria-label="Resources" className="lg:border-l lg:border-border lg:pl-6">
            <ColHeading>Resources</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {RESOURCE_LINKS.map((l) => (
                <li key={l.label}>
                  <FooterLink to={l.to}>{l.label}</FooterLink>
                </li>
              ))}
            </ul>
          </RevealItem>

          {/* OMR modes column */}
          <RevealItem className="lg:border-l lg:border-border lg:pl-6">
            <ColHeading>OMR modes</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {OMR_MODES.map((m) => (
                <FeatureItem key={m}>{m}</FeatureItem>
              ))}
            </ul>
          </RevealItem>

          {/* capabilities column */}
          <RevealItem className="lg:border-l lg:border-border lg:pl-6">
            <ColHeading>Capabilities</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {CAPABILITIES.map((c) => (
                <FeatureItem key={c}>{c}</FeatureItem>
              ))}
            </ul>
          </RevealItem>

          {/* trust column */}
          <RevealItem className="lg:border-l lg:border-border lg:pl-6">
            <ColHeading>Why DoxaEd OMR</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {TRUST_POINTS.map((t) => (
                <li key={t} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <MaterialIcon name="task" className="mt-0.5 size-3.5 shrink-0 text-success" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </RevealItem>

          {/* contact column — real mailto + real site only */}
          <RevealItem className="lg:border-l lg:border-border lg:pl-6">
            <ColHeading>Get in touch</ColHeading>
            <ul className="mt-4 space-y-2.5">
              <li>
                <a href="mailto:hello@doxaed.com" className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
                  <MaterialIcon name="task" className="size-3.5 shrink-0 text-primary" />
                  hello@doxaed.com
                </a>
              </li>
              <li>
                <a href="mailto:support@doxaed.com" className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
                  <MaterialIcon name="task" className="size-3.5 shrink-0 text-primary" />
                  support@doxaed.com
                </a>
              </li>
              <li>
                <a href="https://doxaed.com" rel="noreferrer" className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
                  <MaterialIcon name="devices" className="size-3.5 shrink-0 text-primary" />
                  doxaed.com
                </a>
              </li>
            </ul>
          </RevealItem>
        </div>

        {/* bottom bar */}
        <RevealItem className="mt-14 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 sm:flex-row">
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
            <p className="font-mono text-xs text-muted-foreground">© 2026 DoxaEd OMR</p>
            <Link to="/terms" className="text-xs text-muted-foreground transition-colors hover:text-foreground">
              Terms
            </Link>
            <Link to="/privacy" className="text-xs text-muted-foreground transition-colors hover:text-foreground">
              Privacy
            </Link>
          </div>
          <p className="text-center text-xs text-muted-foreground">
            Built for tutors, coaching centres, schools &amp; competitive-exam prep
          </p>
          <a href="#top" className="group flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground">
            Back to top
            <MaterialIcon name="arrow" className="size-3.5 -rotate-90 transition-transform duration-200 group-hover:-translate-y-0.5" />
          </a>
        </RevealItem>
      </Reveal>
    </footer>
  )
}
