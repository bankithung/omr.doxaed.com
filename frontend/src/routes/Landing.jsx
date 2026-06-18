import { useEffect } from "react"
import { MotionConfig } from "framer-motion"
import { spring } from "./landing/motion/tokens"
import LandingNav, { ScrollRail } from "./landing/LandingNav"
import Hero from "./landing/Hero"
import Centerpiece from "./landing/Centerpiece"
import Bento from "./landing/Bento"
import Marquee from "./landing/Marquee"
import CTA from "./landing/CTA"
import Footer from "./landing/Footer"

/**
 * OMRFlow cinematic landing — a SELF-CONTAINED DARK canvas.
 *
 * This route owns its dark look in a contained `.landing-cinematic` wrapper with
 * EXPLICIT colors (near-black bg + light text + brand indigo/teal glows). It does
 * NOT use the app's light `--background/--foreground` theme tokens, and it does
 * NOT alter the global theme or any other route. Gradients/glow/aurora are allowed
 * here only. `<MotionConfig reducedMotion="user">` makes every motion hook honour
 * prefers-reduced-motion; the Centerpiece renders a static end-state under it.
 *
 * Page order: Nav → Hero → Centerpiece (pinned 4-act scrub) → Bento → Marquee → CTA → Footer.
 */
export default function Landing() {
  // Force a dark surface for this route even though the app is light, without
  // touching the global theme: paint the document background while mounted so
  // there is no light flash above/below the fixed wrapper, then restore on unmount.
  useEffect(() => {
    const prevBg = document.body.style.backgroundColor
    document.body.style.backgroundColor = "#05060a"
    return () => {
      document.body.style.backgroundColor = prevBg
    }
  }, [])

  return (
    <MotionConfig reducedMotion="user" transition={spring.smooth}>
      <div className="landing-cinematic relative min-h-screen overflow-x-hidden bg-[#05060a] text-white antialiased">
        <ScrollRail />
        <LandingNav />
        <Hero />
        <Centerpiece />
        <Bento />
        <Marquee />
        <CTA />
        <Footer />
      </div>
    </MotionConfig>
  )
}
