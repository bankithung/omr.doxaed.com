import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * About — honest and modest. What DoxaEd OMR is, the mission, and the principles
 * the product is actually built on. Deliberately NO fabricated team bios,
 * funding, customer counts or testimonials — only what is true of the product.
 */

const PRINCIPLES = [
  {
    icon: "shield",
    title: "Server-side grading",
    body: "Every sheet is graded against its own stored answer key on the server, never in the browser — so a score can't be tampered with client-side.",
  },
  {
    icon: "task",
    title: "Never guessed",
    body: "Faint, double-marked or missing reads are routed to a review queue with the cropped bubble image — not silently guessed. You stay in control of the call.",
  },
  {
    icon: "lock",
    title: "Encrypted PII",
    body: "Student names and roll numbers are encrypted at rest, and only what a public result needs is ever exposed on the portal.",
  },
  {
    icon: "folder",
    title: "Owner-scoped",
    body: "Every test, sheet and result belongs to exactly one owner or organisation. Access is role-checked and grading actions are auditable.",
  },
]

const FACTS = [
  { icon: "shuffle", label: "A unique, shuffled sheet for every student" },
  { icon: "scan", label: "Scan from any phone or scanner" },
  { icon: "analytics", label: "Item analysis & two-page report cards" },
  { icon: "devices", label: "Works at omr.doxaed.com — nothing to install" },
]

export default function About() {
  return (
    <PublicLayout>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px]"
          style={{
            background:
              "radial-gradient(55% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 12%, transparent), transparent 72%)",
          }}
        />
        <SectionContainer className="pt-14 pb-8 sm:pt-16 text-center">
          <FadeInUp className="mx-auto max-w-2xl">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              About
            </span>
            <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Fair, fast, <span className="text-primary">auditable</span> grading
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              DoxaEd OMR is an optical-mark-recognition platform for generating
              shuffled exam answer sheets, scanning them, and producing
              auto-graded results and analytics — for tutors, coaching centres and
              schools.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Mission ────────────────────────────────────────────────────────── */}
      <SectionContainer className="pt-0">
        <div className="mx-auto grid max-w-5xl items-start gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
          <FadeInUp>
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Our mission
            </span>
            <h2 className="mt-3 text-2xl font-medium tracking-tight text-foreground sm:text-3xl">
              Make fair, fast, auditable exam grading accessible to everyone who teaches
            </h2>
            <div className="mt-5 space-y-4 text-base leading-relaxed text-muted-foreground">
              <p>
                Grading a stack of bubble sheets by hand is slow, error-prone and
                hard to defend when a student questions a mark. DoxaEd OMR exists
                to take that work off the table — without trading away rigour.
              </p>
              <p>
                The same generate → scan → grade → analyse loop scales from a
                single tutor running a weekly quiz to a coaching centre grading
                hundreds of sheets in one pass. Every step is shuffled to deter
                copying, graded against a stored key, and recorded so the result
                can be explained later.
              </p>
              <p>
                We keep the product honest: we don't guess uncertain reads, we
                don't expose more student data than a result needs, and we keep
                every record owned and auditable.
              </p>
            </div>
          </FadeInUp>

          <FadeInUp delay={0.1}>
            <div className="rounded-xl border border-border bg-card p-6">
              <p className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                What DoxaEd OMR does
              </p>
              <ul className="mt-4 space-y-3.5">
                {FACTS.map((f) => (
                  <li key={f.label} className="flex items-start gap-3 text-sm text-foreground">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                      <MaterialIcon name={f.icon} className="size-4" />
                    </span>
                    <span className="pt-1.5">{f.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </FadeInUp>
        </div>
      </SectionContainer>

      {/* ── Principles ─────────────────────────────────────────────────────── */}
      <SectionContainer className="border-t border-border">
        <FadeInUp className="mx-auto max-w-2xl text-center">
          <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Principles
          </span>
          <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            How we build
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
            Four commitments that shape every grading decision the platform makes.
          </p>
        </FadeInUp>

        <Reveal as="div" className="mx-auto mt-12 grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PRINCIPLES.map((p) => (
            <RevealItem
              key={p.title}
              className="flex h-full flex-col rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong"
            >
              <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                <MaterialIcon name={p.icon} className="size-5" />
              </span>
              <h3 className="mt-4 text-base font-medium text-foreground">{p.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{p.body}</p>
            </RevealItem>
          ))}
        </Reveal>
      </SectionContainer>

      {/* ── Contact + CTA ──────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-t border-border">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(50% 60% at 50% 50%, color-mix(in oklch, var(--color-primary) 10%, transparent), transparent 70%)",
          }}
        />
        <SectionContainer>
          <Reveal className="mx-auto max-w-2xl text-center">
            <RevealItem as="h2" className="text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              Questions about DoxaEd OMR?
            </RevealItem>
            <RevealItem as="p" className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              We're happy to help you decide if it fits your tests. Reach out, or
              just create a free account and try it on your next exam.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/contact">Contact us</Link>
              </Button>
            </RevealItem>
            <RevealItem as="p" className="mt-5 font-mono text-xs text-muted-foreground">
              doxaed@gmail.com · doxaed.com
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
