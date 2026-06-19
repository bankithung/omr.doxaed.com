import { MotionConfig } from "framer-motion"

import LandingNav from "./landing/LandingNav"
import Hero from "./landing/Hero"
import TrustStrip from "./landing/TrustStrip"
import Bento from "./landing/Bento"
import HowItWorks from "./landing/HowItWorks"
import UseCases from "./landing/UseCases"
import TrustSection from "./landing/TrustSection"
import CTA from "./landing/CTA"
import Footer from "./landing/Footer"

/**
 * DoxaEd OMR landing — a flat, Supabase-shaped marketing page on the app's
 * semantic tokens, so it is dark-first by default and flips with the theme.
 *
 * Page order (Supabase architecture): Nav → centered Hero + product visual →
 * trust strip → Bento feature grid → "How it works" deep-dive (animated
 * graphics) → "Built for" use-cases → "Why DoxaEd OMR" trust band → CTA band →
 * Footer. Surfaces + 1px hairline borders + one brand accent (Supabase green) +
 * restraint carry the premium look; the only subtle gradients are faint brand
 * glows behind the hero / CTA headings + mask-fades.
 *
 * Motion = the Supabase language (fadeInUp scroll-reveals with staggered
 * children, a CSS marquee trust strip, restrained hover lifts). `<MotionConfig
 * reducedMotion="user">` makes every framer-motion hook honour
 * prefers-reduced-motion; the reveal helpers also render static fallbacks.
 *
 * framer-motion ships only in this (lazy) Landing chunk.
 */
export default function Landing() {
  return (
    <MotionConfig reducedMotion="user">
      <div id="top" className="min-h-screen bg-background text-foreground antialiased">
        <LandingNav />
        <main>
          <Hero />
          <TrustStrip />
          <Bento />
          <HowItWorks />
          <UseCases />
          <TrustSection />
          <CTA />
        </main>
        <Footer />
      </div>
    </MotionConfig>
  )
}
