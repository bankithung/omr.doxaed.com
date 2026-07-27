import { Link } from "react-router-dom"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { DealOut, ScanSheet, AnalyticsChart } from "@/routes/landing/ProductGraphics"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * BuiltForPage (/built-for) — the dedicated "who it's for" page. The landing has
 * a compact "Built for" strip; this page gives each audience a proper
 * explanation + a concrete "what you get" checklist + a fitting animated graphic
 * (alternating layout). Honest positioning only — every point is real product
 * behaviour, no fabricated customers or numbers.
 */

const AUDIENCES = [
  {
    icon: "groups",
    label: "Private tutors",
    title: "Weekly tests for a handful of students, graded the same evening",
    body: "Stop hand-marking quizzes or copying the same paper for everyone. Generate a unique, shuffled sheet for each student, scan the stack from your phone, and have scored results to share before the day is out.",
    points: [
      "A unique shuffled sheet per student, no two identical orders",
      "Scan with the phone you already have, no scanner needed",
      "Auto-graded against the stored key, results the same evening",
      "Free to start: the free plan fits a single tutor's weekly tests",
    ],
    graphic: <ScanSheet />,
  },
  {
    icon: "layers",
    label: "Coaching centres",
    title: "Batch whole cohorts and rank them across every test",
    body: "Built for volume. Generate shuffled sheets for entire batches at once, auto-grade hundreds of OMRs in a single pass, and turn each test into rankings and item analysis you can compare across the term.",
    points: [
      "Batch-generate shuffled sheets for whole batches",
      "Scan & auto-grade hundreds of sheets in one pass",
      "Item analysis + rankings to compare students across tests",
      "Folders, organisations and roles for your teaching staff",
    ],
    graphic: <DealOut />,
  },
  {
    icon: "checklist",
    label: "Schools",
    title: "Standardise unit tests across every section",
    body: "Write one question bank and reuse it across sections so every class sits a comparable paper. Roster-native sheets identify students automatically, and parents get a clean public result with printable report cards.",
    points: [
      "One shared question bank across classes and sections",
      "Roster-native sheets, students auto-identified by roll",
      "Two-page printable report cards per student",
      "A public result portal for parents, owner-scoped & auditable",
    ],
    graphic: <ScanSheet variant="full" />,
  },
  {
    icon: "target",
    label: "Competitive-exam prep",
    title: "NEET- and UPSC-style mocks, marked exactly to the rules",
    body: "Run sectional mocks with the marking schemes real exams use. Configure multi-mark and negative-marking rules per test, then read percentiles and per-topic accuracy to show students exactly where to focus.",
    points: [
      "Sectional papers with per-section configuration",
      "Configurable multi-mark & negative-marking rules",
      "Percentiles and rank within the cohort",
      "Per-topic mastery so students know what to revise",
    ],
    graphic: <AnalyticsChart label="Per-topic accuracy" />,
  },
]

function Audience({ icon, label, title, body, points, graphic, flip }) {
  return (
    <SectionContainer className="border-t border-border">
 <div className="mx-auto grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
        <FadeInUp className={cn(flip && "lg:order-2")}>
          <span className="inline-flex items-center gap-2 font-mono text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <span className="flex size-7 items-center justify-center rounded-md border border-border bg-surface-2 text-indigo">
              <MaterialIcon name={icon} className="size-4" />
            </span>
            {label}
          </span>
          <h2 className="mt-4 text-2xl font-medium tracking-tight text-foreground sm:text-3xl">
            {title}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">{body}</p>
          <ul className="mt-6 space-y-3">
            {points.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm text-foreground">
                <MaterialIcon name="task" className="mt-0.5 size-4 shrink-0 text-indigo" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </FadeInUp>

        <div className={cn(flip && "lg:order-1")}>{graphic}</div>
      </div>
    </SectionContainer>
  )
}

export default function BuiltForPage() {
  return (
    <PublicLayout>
      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px]"
          style={{
            background:
              "radial-gradient(55% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 12%, transparent), transparent 72%)",
          }}
        />
        <SectionContainer className="pt-14 pb-6 text-center sm:pt-16">
 <FadeInUp className="mx-auto ">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Built for
            </span>
 <h1 className="mx-auto mt-3 text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              One workflow, from a single tutor to a whole{" "}
              <span className="text-indigo">school</span>
            </h1>
 <p className="mx-auto mt-5 text-base text-muted-foreground sm:text-lg">
              The same generate → scan → grade → analyse loop scales from a weekly
              quiz to batch-graded competitive mocks. Here is what it looks like
              for each.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Audiences ──────────────────────────────────────────────────────── */}
      {AUDIENCES.map((a, i) => (
        <Audience key={a.label} {...a} flip={i % 2 === 1} />
      ))}

      {/* ── CTA ────────────────────────────────────────────────────────────── */}
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
              Whatever you teach, grading is the same loop
            </RevealItem>
 <RevealItem as="p" className="mx-auto mt-4 text-base text-muted-foreground sm:text-lg">
              Every plan includes the full engine, shuffled sheets, server-side
              grading, the review queue and analytics. Start free and scale when
              your batches do.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/pricing">See pricing</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
