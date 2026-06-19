import { useReducedMotion } from "framer-motion"
import MaterialIcon from "./MaterialIcon"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem, FadeInUp } from "./motion/reveal"

const FEATURES = [
  {
    icon: "shuffle",
    title: "Per-student shuffle",
    body: "Question and option order is shuffled uniquely per student; every sheet stores its own answer key, so grading stays exact.",
    className: "md:col-span-12 xl:col-span-6 xl:row-span-2",
    big: true,
  },
  { icon: "groups", title: "Roster-native", body: "Start from a class list — name students or just pick a count.", className: "md:col-span-6 xl:col-span-3" },
  { icon: "checklist", title: "One question bank", body: "Write MCQs once; reuse across tests and sections.", className: "md:col-span-6 xl:col-span-3" },
  { icon: "scan", title: "Scan from any device", body: "Phone, scanner, or a stack of photos — auto-aligned by fiducials + QR.", className: "md:col-span-6 xl:col-span-3" },
  { icon: "shield", title: "Never guessed", body: "Faint, double-marked or missing reads go to a review queue — not a guess.", className: "md:col-span-6 xl:col-span-3" },
  { icon: "analytics", title: "Analytics profile", body: "Distributions, toppers, hardest questions, and per-student improvement over time.", className: "md:col-span-12 xl:col-span-6" },
]

// Restrained hover lift (compositor-only y), gated off reduced motion.
function FeatureCard({ icon, title, body, className, big }) {
  const reduce = useReducedMotion()
  return (
    <RevealItem
      className={className}
      whileHover={reduce ? undefined : { y: -2 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
    >
      <div className="group/tile flex h-full flex-col rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong hover:shadow-md">
        <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
          <MaterialIcon name={icon} className="size-5" />
        </span>
        <div className="mt-4 flex items-start justify-between gap-3">
          <h3 className={["font-medium text-foreground", big ? "text-xl" : "text-base"].join(" ")}>{title}</h3>
          <MaterialIcon
            name="arrow"
            className="size-4 shrink-0 -translate-x-1 text-muted-foreground opacity-0 transition-all duration-200 group-hover/tile:translate-x-0 group-hover/tile:opacity-100"
          />
        </div>
        <p className={["mt-1.5 text-muted-foreground", big ? "text-base" : "text-sm"].join(" ")}>{body}</p>
      </div>
    </RevealItem>
  )
}

/**
 * Bento — a 12-col feature grid of flat Panels (Supabase bento). fadeInUp
 * staggered reveal as the grid scrolls in; restrained per-card hover lift +
 * border-strengthen. All app tokens, theme-aware, flat (no gradients).
 */
export default function Bento() {
  return (
    <SectionContainer id="features">
      <FadeInUp className="mx-auto max-w-2xl text-center">
        <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Why DoxaEd OMR
        </span>
        <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
          Everything you need to grade faster — and fairer
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
          From a class list to a graded, analysed exam — every step is shuffled, scanned,
          and auditable.
        </p>
      </FadeInUp>

      <Reveal
        as="div"
        className="mx-auto mt-12 grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-12"
      >
        {FEATURES.map((f) => (
          <FeatureCard key={f.title} {...f} />
        ))}
      </Reveal>
    </SectionContainer>
  )
}
