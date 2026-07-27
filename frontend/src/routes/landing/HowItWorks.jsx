import MaterialIcon from "./MaterialIcon"
import { ScanSheet, AnalyticsChart, DealOut } from "./ProductGraphics"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem, FadeInUp } from "./motion/reveal"

const STEPS = [
  {
    n: "01",
    icon: "checklist",
    title: "Build once",
    body: "Write your MCQs into one question bank and pick a roster, a named class list or just a count of students.",
  },
  {
    n: "02",
    icon: "shuffle",
    title: "Generate unique sheets",
    body: "Every student gets a sheet with question and option order shuffled, each carrying its own stored answer key and a QR code.",
  },
  {
    n: "03",
    icon: "scan",
    title: "Scan & auto-grade",
    body: "Upload from any phone or scanner. Sheets are auto-aligned by fiducials; low-confidence reads go to a review queue, never a guess.",
  },
  {
    n: "04",
    icon: "analytics",
    title: "Analyse & share",
    body: "Get score distributions, toppers, the hardest questions, item analysis, and two-page report cards, plus a public result portal.",
  },
]

function StepCard({ n, icon, title, body }) {
  return (
    <RevealItem className="flex h-full flex-col rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong">
      <div className="flex items-center justify-between">
        <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-indigo">
          <MaterialIcon name={icon} className="size-5" />
        </span>
        <span className="font-mono text-sm font-medium tabular text-muted-foreground">{n}</span>
      </div>
      <h3 className="mt-4 text-base font-medium text-foreground">{title}</h3>
      <p className="mt-1.5 text-sm text-muted-foreground">{body}</p>
    </RevealItem>
  )
}

/**
 * HowItWorks — the Supabase "how it works" flow: a section header + a row of
 * numbered flat-panel steps that fadeInUp-stagger in, plus a flat preview panel
 * showing the shuffle → graded story with real BubbleSheets. All app tokens,
 * theme-aware, flat. Replaces the old cinematic scroll-jacked centerpiece.
 */
export default function HowItWorks() {
  return (
    <SectionContainer id="how-it-works" className="border-t border-border">
 <FadeInUp className="mx-auto text-center">
        <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          How it works
        </span>
        <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
          From a class list to graded analytics, in four steps
        </h2>
      </FadeInUp>

 <Reveal as="div" className="mx-auto mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => (
          <StepCard key={s.n} {...s} />
        ))}
      </Reveal>

      {/* Deep-dive: each beat illustrated with a flat ANIMATED product graphic.
          Generate (deal-out) → Scan (scan-line sweep) → Analyse (drawn chart). */}
 <div className="mx-auto mt-12 grid gap-4 lg:grid-cols-2">
        <FadeInUp className="lg:col-span-2">
          <div className="rounded-2xl border border-border bg-card p-5 sm:p-6">
            <div className="mb-4 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              <MaterialIcon name="shuffle" className="size-3.5 text-indigo" />
              Generate shuffled sheets
            </div>
            <DealOut />
          </div>
        </FadeInUp>

        <FadeInUp>
          <div className="h-full rounded-2xl border border-border bg-card p-5 sm:p-6">
            <div className="mb-4 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              <MaterialIcon name="scan" className="size-3.5 text-indigo" />
              Scan &amp; auto-grade
            </div>
            <ScanSheet />
          </div>
        </FadeInUp>

        <FadeInUp delay={0.1}>
          <div className="flex h-full flex-col rounded-2xl border border-border bg-card p-5 sm:p-6">
            <div className="mb-4 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              <MaterialIcon name="analytics" className="size-3.5 text-indigo" />
              Analyse results
            </div>
            <AnalyticsChart label="Class score distribution" />
            <p className="mt-4 text-sm text-muted-foreground">
              Score distributions, toppers, the hardest questions and per-student
              improvement, every test becomes a full analytics profile.
            </p>
          </div>
        </FadeInUp>
      </div>
    </SectionContainer>
  )
}
