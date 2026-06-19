import { MotionConfig } from "framer-motion"

import LandingNav from "@/routes/landing/LandingNav"
import Footer from "@/routes/landing/Footer"

/**
 * PublicLayout — the shared chrome for standalone public marketing pages
 * (Pricing, Features, About, Contact). It reuses the landing's exact sticky
 * `LandingNav` + `Footer` on `bg-background`, so every public page reads as one
 * cohesive Supabase-shaped marketing site — NOT the logged-in app shell.
 *
 * `<MotionConfig reducedMotion="user">` mirrors the landing so every
 * framer-motion reveal inside a page honours prefers-reduced-motion (the reveal
 * helpers also ship static fallbacks). framer-motion stays in the lazy page
 * chunks that import this layout.
 */
export default function PublicLayout({ children }) {
  return (
    <MotionConfig reducedMotion="user">
      <div id="top" className="min-h-screen bg-background text-foreground antialiased">
        <LandingNav />
        <main id="main">{children}</main>
        <Footer />
      </div>
    </MotionConfig>
  )
}
