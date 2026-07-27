import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import { Reveal, RevealItem } from "@/routes/landing/motion/reveal"

/**
 * NotFound — a clean, branded 404 rendered in the shared PublicLayout (landing
 * nav + footer). Centered, fully responsive, with primary links back to Home and
 * Help. This is the catch-all `path="*"` route and must be declared LAST.
 */
export default function NotFound() {
  return (
    <PublicLayout>
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(55% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 12%, transparent), transparent 72%)",
          }}
        />
        <SectionContainer className="flex min-h-[60vh] flex-col items-center justify-center py-24 text-center">
 <Reveal className="mx-auto ">
            <RevealItem
              as="p"
              className="font-mono text-7xl font-semibold tracking-tight text-indigo sm:text-8xl"
            >
              404
            </RevealItem>
            <RevealItem
              as="h1"
              className="mt-4 text-3xl font-medium tracking-tight text-foreground sm:text-4xl"
            >
              Page not found
            </RevealItem>
            <RevealItem as="p" className="mx-auto mt-4 max-w-md text-base text-muted-foreground sm:text-lg">
              The page you're looking for doesn't exist or may have moved. Let's
              get you back on track.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/">Back to home</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/help">Getting started</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
