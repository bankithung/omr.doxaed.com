import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import BubbleSheet from "./BubbleSheet"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem } from "./motion/reveal"

// E2E CONTRACT: the <h1> accessible name MUST match /Grade a stack of bubble sheets/.
// It is a single plain <h1>; the two visual lines are inline spans inside it, so
// the accessible name resolves to the full "Grade a stack of bubble sheets in minutes."

/**
 * Hero — Supabase two-line headline (big, medium weight, tight tracking) with the
 * accent line in `text-primary`, subcopy, "Start free" / "Sign in" CTAs, and a
 * flat Panel holding the BubbleSheet visual. A VERY faint radial glow sits behind
 * the headline (the single allowed subtle gradient — tasteful, Supabase-level).
 * fadeInUp staggered entrance; all motion honours reduced-motion via Reveal.
 */
export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Faint hero glow — the one allowed subtle gradient, very low opacity. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[480px]"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 14%, transparent), transparent 72%)",
        }}
      />

      <SectionContainer className="pt-12 pb-12 sm:pt-16 md:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          {/* Copy column */}
          <Reveal className="max-w-2xl">
            <RevealItem>
              <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
                <span className="relative flex size-1.5">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-60" />
                  <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
                </span>
                <span className="font-mono uppercase tracking-[0.14em]">Generate · Scan · Grade · Analyse</span>
              </span>
            </RevealItem>

            <RevealItem as="h1" className="mt-6 text-4xl font-medium tracking-tight text-foreground sm:text-5xl sm:leading-[1.05] lg:text-7xl">
              <span className="block">Grade a stack of bubble sheets</span>
              <span className="block text-primary">in minutes.</span>
            </RevealItem>

            <RevealItem as="p" className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              One question bank. One roster. A unique, shuffled sheet for every student —
              scanned, auto-graded, and turned into analytics.
            </RevealItem>

            <RevealItem className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button size="lg" asChild className="h-11 px-5 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-5 text-sm">
                <Link to="/login">Sign in</Link>
              </Button>
            </RevealItem>

            <RevealItem as="p" className="mt-5 text-xs text-muted-foreground">
              <span className="font-mono">No card required</span> · Works with any phone or scanner ·
              Built for tutors, coaching centres &amp; schools
            </RevealItem>
          </Reveal>

          {/* Visual column — flat panel with the OMR sheet */}
          <Reveal className="relative mx-auto w-full max-w-[360px] lg:max-w-[420px]">
            <RevealItem className="rounded-2xl border border-border bg-card p-3 shadow-lg transition-colors hover:border-border-strong sm:p-4">
              <BubbleSheet seed={7} name="Asha Devi" roll="101" className="aspect-[200/264]" />
            </RevealItem>
          </Reveal>
        </div>
      </SectionContainer>
    </section>
  )
}
