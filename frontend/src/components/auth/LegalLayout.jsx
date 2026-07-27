import { Link } from "react-router-dom"

import LandingNav from "@/routes/landing/LandingNav"

const LAST_UPDATED = "19 June 2026"

// Clean, centered legal layout: the SAME shared home-page header (LandingNav),
// then the title + last-updated date, review-template notice, and a readable
// prose body. App tokens only.
export default function LegalLayout({ title, children }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <LandingNav />

 <main className="mx-auto px-4 py-10 sm:py-14">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">Last updated: {LAST_UPDATED}</p>
        </div>

        <div
          role="note"
          className="mt-6 rounded-lg border border-[var(--color-warning)]/30 bg-[color-mix(in_oklch,var(--color-warning)_10%,transparent)] px-4 py-3 text-sm text-foreground"
        >
          <strong>Template for review</strong>, have legal counsel finalise before
          production.
        </div>

        <article className="legal-prose mt-8 space-y-7 text-sm leading-relaxed text-foreground">
          {children}
        </article>

        <footer className="mt-12 border-t border-border pt-6 text-sm text-muted-foreground">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <Link to="/terms" className="text-indigo underline-offset-4 hover:underline">
              Terms of Service
            </Link>
            <Link to="/privacy" className="text-indigo underline-offset-4 hover:underline">
              Privacy Policy
            </Link>
            <span className="ml-auto">© DoxaEd OMR</span>
          </div>
        </footer>
      </main>
    </div>
  )
}

// Section heading + body helpers used by both legal pages.
export function Section({ heading, children }) {
  return (
    <section className="space-y-2.5">
      <h2 className="text-lg font-semibold tracking-tight text-foreground">{heading}</h2>
      {children}
    </section>
  )
}

export function P({ children }) {
  return <p className="text-muted-foreground">{children}</p>
}

export function List({ items }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5 text-muted-foreground marker:text-muted-foreground/60">
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ul>
  )
}
