import MaterialIcon from "./MaterialIcon"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem, FadeInUp } from "./motion/reveal"

// Real positioning only — who DoxaEd OMR is actually built for.
const USE_CASES = [
  {
    icon: "groups",
    title: "Private tutors",
    body: "Run weekly tests for a handful of students without printing a different paper by hand — generate, scan from your phone, and share scores the same evening.",
  },
  {
    icon: "layers",
    title: "Coaching centres",
    body: "Batch-generate shuffled sheets for whole batches, grade hundreds of OMRs in one pass, and rank students with item analysis across tests.",
  },
  {
    icon: "checklist",
    title: "Schools",
    body: "Standardise unit tests across sections with one question bank, roster-native sheets, two-page report cards and a public result portal for parents.",
  },
  {
    icon: "target",
    title: "Competitive-exam prep",
    body: "NEET- and UPSC-style sectional mocks with configurable multi-mark and negative-marking rules, percentiles, and per-topic accuracy.",
  },
]

/**
 * UseCases — the Supabase "built for" strip. Real positioning (tutors, coaching
 * centres, schools, competitive-exam prep) on flat panels with a fadeInUp
 * staggered reveal. App tokens, theme-aware, flat.
 */
export default function UseCases() {
  return (
    <SectionContainer id="use-cases" className="border-t border-border">
      <FadeInUp className="mx-auto max-w-2xl text-center">
        <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Built for
        </span>
        <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
          One workflow, from a single tutor to a whole school
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
          The same generate → scan → grade → analyse loop scales from a weekly
          quiz to batch-graded competitive mocks.
        </p>
      </FadeInUp>

      <Reveal as="div" className="mx-auto mt-12 grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2">
        {USE_CASES.map((u) => (
          <RevealItem
            key={u.title}
            className="flex h-full gap-4 rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong"
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
              <MaterialIcon name={u.icon} className="size-5" />
            </span>
            <div>
              <h3 className="text-base font-medium text-foreground">{u.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{u.body}</p>
            </div>
          </RevealItem>
        ))}
      </Reveal>
    </SectionContainer>
  )
}
