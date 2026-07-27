import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import MaterialIcon from "./MaterialIcon"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem } from "./motion/reveal"

/**
 * CTA — a flat closing band on a hairline-topped section. fadeInUp staggered
 * reveal; a very faint brand radial sits behind the heading (the same single
 * allowed subtle glow as the hero). All app tokens, theme-aware, flat.
 */
export default function CTA() {
  return (
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
          <RevealItem>
            <span className="mx-auto flex size-12 items-center justify-center rounded-xl border border-border bg-card text-indigo">
              <MaterialIcon name="layers" className="size-6" />
            </span>
          </RevealItem>
          <RevealItem as="h2" className="mx-auto mt-6 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            Stop grading by hand.
          </RevealItem>
 <RevealItem as="p" className="mx-auto mt-4 text-base text-muted-foreground sm:text-lg">
            Create your first test free and grade your next exam in minutes, shuffled sheets,
            auto-grading and analytics included.
          </RevealItem>
          <RevealItem className="mt-8 flex justify-center">
            <Button size="lg" asChild className="h-11 px-6 text-sm">
              <Link to="/register">Start free</Link>
            </Button>
          </RevealItem>
          <RevealItem as="p" className="mt-4 font-mono text-xs text-muted-foreground">
            No card required · Cancel anytime
          </RevealItem>
        </Reveal>
      </SectionContainer>
    </section>
  )
}
