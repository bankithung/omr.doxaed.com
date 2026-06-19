import MaterialIcon from "./MaterialIcon"
import BubbleSheet, { ShuffledSheet, GradedSheet } from "./BubbleSheet"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem, FadeInUp } from "./motion/reveal"

const STEPS = [
  {
    n: "01",
    icon: "checklist",
    title: "Build once",
    body: "Write your MCQs into one question bank and pick a roster — a named class list or just a count of students.",
  },
  {
    n: "02",
    icon: "shuffle",
    title: "Generate unique sheets",
    body: "Every student gets a sheet with question and option order shuffled — each carrying its own stored answer key and a QR code.",
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
    body: "Get score distributions, toppers, the hardest questions, item analysis, and two-page report cards — plus a public result portal.",
  },
]

function StepCard({ n, icon, title, body }) {
  return (
    <RevealItem className="flex h-full flex-col rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong">
      <div className="flex items-center justify-between">
        <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
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
      <FadeInUp className="mx-auto max-w-2xl text-center">
        <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          How it works
        </span>
        <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
          From a class list to graded analytics — in four steps
        </h2>
      </FadeInUp>

      <Reveal as="div" className="mx-auto mt-12 grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => (
          <StepCard key={s.n} {...s} />
        ))}
      </Reveal>

      {/* Sheet story — one master, two shuffled, one graded; flat panel */}
      <FadeInUp
        delay={0.1}
        className="mx-auto mt-12 grid max-w-5xl grid-cols-2 gap-4 rounded-2xl border border-border bg-card p-4 sm:grid-cols-4 sm:p-6"
      >
        <div className="rounded-xl border border-border bg-surface-2 p-2">
          <BubbleSheet seed={1} name="Master" roll="000" className="aspect-[200/264]" />
        </div>
        <div className="rounded-xl border border-border bg-surface-2 p-2">
          <ShuffledSheet seed={3} name="Asha D." roll="101" className="aspect-[200/264]" />
        </div>
        <div className="rounded-xl border border-border bg-surface-2 p-2">
          <ShuffledSheet seed={5} name="Rahul K." roll="102" className="aspect-[200/264]" />
        </div>
        <div className="rounded-xl border border-border bg-surface-2 p-2">
          <GradedSheet seed={7} name="Asha D." roll="101" score="14/15" className="aspect-[200/264]" />
        </div>
      </FadeInUp>
    </SectionContainer>
  )
}
