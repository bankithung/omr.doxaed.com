import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import SectionContainer from "./SectionContainer"
import { DashboardPreview } from "./ProductGraphics"
import { Reveal, RevealItem, FadeInUp } from "./motion/reveal"

// E2E CONTRACT: the <h1> accessible name MUST match /Grade a stack of bubble sheets/.
// It is a single plain <h1>; the two visual lines are inline spans inside it, so
// the accessible name resolves to the full "Grade a stack of bubble sheets in minutes."

/**
 * Hero — Supabase's exact hero shape: a CENTERED column (eyebrow + big two-line
 * headline + subcopy + CTA row + "no card" line), then a LARGE animated product
 * visual BELOW it (Supabase shows a dashboard under its hero). No side card.
 *
 * A VERY faint radial glow sits behind the headline (the single allowed subtle
 * gradient — Supabase-level). fadeInUp staggered entrance; the product preview
 * rises in beneath and animates its internals on view. All motion honours
 * reduced-motion via Reveal / the graphics' reduced-motion fallbacks.
 */
export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Faint hero glow — the one allowed subtle gradient, very low opacity. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[560px]"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 14%, transparent), transparent 72%)",
        }}
      />

      <SectionContainer className="pt-12 pb-16 sm:pt-16 md:pt-20">
        {/* Centered copy column */}
        <Reveal className="mx-auto max-w-3xl text-center">
          <RevealItem className="flex justify-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
              <span className="relative flex size-1.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-60" />
                <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
              </span>
              <span className="font-mono uppercase tracking-[0.14em]">Generate · Scan · Grade · Analyse</span>
            </span>
          </RevealItem>

          <RevealItem as="h1" className="mx-auto mt-6 max-w-3xl text-4xl font-medium tracking-tight text-foreground sm:text-5xl sm:leading-[1.05] lg:text-7xl">
            <span className="block">Grade a stack of bubble sheets</span>
            <span className="block text-primary">in minutes.</span>
          </RevealItem>

          <RevealItem as="p" className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
            One question bank. One roster. A unique, shuffled sheet for every student —
            scanned, auto-graded, and turned into analytics.
          </RevealItem>

          <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row sm:items-center">
            <Button size="lg" asChild className="h-11 px-5 text-sm">
              <Link to="/register">Start free</Link>
            </Button>
            <Button size="lg" variant="outline" asChild className="h-11 px-5 text-sm">
              <Link to="/login">Sign in</Link>
            </Button>
          </RevealItem>

          <RevealItem as="p" className="mx-auto mt-5 text-xs text-muted-foreground">
            <span className="font-mono">No card required</span> · Works with any phone or scanner ·
            Built for tutors, coaching centres &amp; schools
          </RevealItem>
        </Reveal>

        {/* Large animated product visual BELOW the hero (Supabase dashboard shot) */}
        <FadeInUp delay={0.15} className="mx-auto mt-14 max-w-5xl sm:mt-16">
          <DashboardPreview />
          <p className="mt-3 text-center font-mono text-[11px] text-muted-foreground">
            A real test in DoxaEd OMR — graded, distributed, and analysed.
          </p>
        </FadeInUp>
      </SectionContainer>
    </section>
  )
}
