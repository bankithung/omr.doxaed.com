import { useEffect } from "react"
import { motion, useMotionValue, useSpring, useReducedMotion } from "framer-motion"
import { usePointerFine } from "./Micro"

/**
 * Atmosphere — filmic overlays for the dark cinematic canvas (landing only).
 *
 *  - landing-grain:   fixed fractal-noise texture, ~5% opacity, mix-blend-overlay
 *  - landing-vignette: soft edge darkening for a framed, cinematic look
 *  - landing-cursor:   a soft brand-tinted glow that trails a real cursor
 *
 * All three are pointer-events:none, fixed, and scoped to `.landing-cinematic`.
 * Grain + cursor are hidden under prefers-reduced-motion (CSS backstop); the
 * cursor only mounts on fine-pointer (hover:hover) devices.
 */
export default function Atmosphere() {
  const reduce = useReducedMotion()
  const fine = usePointerFine()

  const cx = useMotionValue(-1000)
  const cy = useMotionValue(-1000)
  const sx = useSpring(cx, { stiffness: 220, damping: 30, mass: 0.6 })
  const sy = useSpring(cy, { stiffness: 220, damping: 30, mass: 0.6 })
  const cursorActive = fine && !reduce

  useEffect(() => {
    if (!cursorActive) return
    const onMove = (e) => {
      cx.set(e.clientX)
      cy.set(e.clientY)
    }
    window.addEventListener("pointermove", onMove, { passive: true })
    return () => window.removeEventListener("pointermove", onMove)
  }, [cursorActive, cx, cy])

  return (
    <>
      {cursorActive && (
        <motion.div aria-hidden className="landing-cursor" style={{ x: sx, y: sy }} />
      )}
      <div aria-hidden className="landing-vignette" />
      {!reduce && <div aria-hidden className="landing-grain" />}
    </>
  )
}
