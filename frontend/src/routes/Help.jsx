import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * Help — a "Getting started" walkthrough. A real, ordered seven-step flow that
 * mirrors how the product actually works (class + bank → roster → generate &
 * print shuffled sheets → students fill paper → scan from any phone → review
 * low-confidence reads → publish results + analytics). Plus honest tips and
 * links to /faq and /contact. No fabricated timings, videos or support SLAs.
 */

const STEPS = [
  {
    icon: "checklist",
    title: "Create a class and question bank",
    body: "Start by creating a class and building its question bank, the pool of questions a test draws from. This is the source of truth a generated sheet's stored answer key comes from.",
  },
  {
    icon: "groups",
    title: "Add your roster",
    body: "Add the students who'll sit the test. A roster can pre-bubble roll numbers so sheets auto-identify each student when they're scanned back in.",
  },
  {
    icon: "shuffle",
    title: "Generate shuffled OMR sheets and print",
    body: "Generate the answer sheets for the test. Per-student shuffle gives each student a unique question and option order to deter copying, then print the batch on plain paper.",
  },
  {
    icon: "task",
    title: "Students fill the bubbles",
    body: "Hand out the printed sheets. Students fill the bubbles with a pen or pencil on paper, there's no app for them to install and no account for them to create.",
  },
  {
    icon: "scan",
    title: "Scan from any phone",
    body: "Capture the filled sheets with any phone camera or document scanner. The QR code and fiducial markers on each sheet align the scan, so bubbles read correctly whatever device you used.",
  },
  {
    icon: "shield",
    title: "Review low-confidence reads",
    body: "Anything the grader isn't sure about, faint, double-marked or empty bubbles, lands in the review queue with the cropped image, so you confirm the call. Nothing is silently guessed.",
  },
  {
    icon: "analytics",
    title: "Publish results, analytics and report cards",
    body: "Publish the graded results. Each test gets item analysis and two-page report cards, and you can share results through the public result portal, which exposes only what a result needs.",
  },
]

const TIPS = [
  {
    icon: "devices",
    title: "Any device works",
    body: "There's nothing to install for scanning, a regular phone camera is enough, as long as the whole sheet (and its QR + markers) is in frame and reasonably lit.",
  },
  {
    icon: "shuffle",
    title: "Shuffle is safe to grade",
    body: "Per-student shuffling never changes the score: each sheet is always graded against its own stored key, so a different order can't penalise a student.",
  },
  {
    icon: "task",
    title: "Trust the review queue",
    body: "If a read is ambiguous, let it go to review rather than re-bubbling, confirming it there keeps the result auditable and explainable later.",
  },
  {
    icon: "lock",
    title: "Share only what's needed",
    body: "The public result portal surfaces just the fields a result needs. Student PII stays encrypted and scoped to you, you control what's shared.",
  },
]

function StepRow({ step, index }) {
  return (
    <RevealItem
      as="li"
      className="relative flex gap-5 rounded-xl border border-border bg-card p-5 transition-colors hover:border-border-strong sm:p-6"
    >
      <div className="flex flex-col items-center">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 font-mono text-sm font-medium text-indigo">
          {index + 1}
        </span>
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex items-center gap-2">
          <MaterialIcon name={step.icon} className="size-4 shrink-0 text-indigo" />
          <h3 className="text-base font-medium text-foreground">{step.title}</h3>
        </div>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
      </div>
    </RevealItem>
  )
}

export default function Help() {
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
 <FadeInUp className="mx-auto ">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Help
            </span>
 <h1 className="mx-auto mt-3 text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Getting started, <span className="text-indigo">step by step</span>
            </h1>
 <p className="mx-auto mt-5 text-base text-muted-foreground sm:text-lg">
              The full loop from setting up a class to publishing results, seven
              steps that mirror exactly how DoxaEd OMR works.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Numbered flow ──────────────────────────────────────────────────── */}
      <SectionContainer className="pt-0">
 <Reveal as="ol" className="mx-auto grid grid-cols-1 gap-3">
          {STEPS.map((step, i) => (
            <StepRow key={step.title} step={step} index={i} />
          ))}
        </Reveal>
 <FadeInUp className="mx-auto mt-8 ">
          <div className="flex flex-col items-center justify-between gap-3 rounded-xl border border-border bg-surface-1 p-5 sm:flex-row">
            <p className="text-sm text-muted-foreground">
              Ready to run your first test? Create a free account and start at
              step one.
            </p>
            <Button asChild className="h-10 shrink-0 px-5 text-sm">
              <Link to="/register">Start free</Link>
            </Button>
          </div>
        </FadeInUp>
      </SectionContainer>

      {/* ── Tips ───────────────────────────────────────────────────────────── */}
      <SectionContainer className="border-t border-border pt-16">
 <FadeInUp className="mx-auto text-center">
          <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Tips
          </span>
          <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            Get the most from each scan
          </h2>
 <p className="mx-auto mt-4 text-base text-muted-foreground">
            A few honest pointers that make grading smoother and results easier to
            defend.
          </p>
        </FadeInUp>

 <Reveal as="div" className="mx-auto mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {TIPS.map((tip) => (
            <RevealItem
              key={tip.title}
              className="flex h-full gap-4 rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong"
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-indigo">
                <MaterialIcon name={tip.icon} className="size-5" />
              </span>
              <div className="min-w-0">
                <h3 className="text-base font-medium text-foreground">{tip.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{tip.body}</p>
              </div>
            </RevealItem>
          ))}
        </Reveal>
      </SectionContainer>

      {/* ── Next steps / CTA ───────────────────────────────────────────────── */}
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
 <Reveal className="mx-auto text-center">
            <RevealItem as="h2" className="text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              Need a hand?
            </RevealItem>
 <RevealItem as="p" className="mx-auto mt-4 text-base text-muted-foreground sm:text-lg">
              Browse common questions in the FAQ, or reach out and we'll help you
              get your first exam graded.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/faq">Read the FAQ</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/contact">Contact us</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
