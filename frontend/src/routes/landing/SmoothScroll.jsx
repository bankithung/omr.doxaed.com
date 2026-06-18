import { useEffect } from "react"
import { frame, cancelFrame, useReducedMotion } from "framer-motion"
import Lenis from "lenis"

/**
 * SmoothScroll — buttery inertial scrolling for the landing route ONLY.
 *
 * Mounts a single Lenis instance and drives its `raf(time)` from framer-motion's
 * shared frame loop (NOT a second requestAnimationFrame), so scroll-linked motion
 * values stay perfectly in sync with no duelling rAF loops. `autoRaf: false`
 * disables Lenis's own loop. Fully torn down on unmount.
 *
 * Skipped entirely under prefers-reduced-motion — the page then uses the native
 * scroll and the Centerpiece renders its static end-state.
 *
 * Self-contained: this never runs in the app; it lives only in the lazy landing
 * chunk and is unmounted the moment the user navigates away.
 */
export default function SmoothScroll() {
  const reduce = useReducedMotion()

  useEffect(() => {
    if (reduce) return
    if (typeof window === "undefined") return

    const lenis = new Lenis({
      autoRaf: false,
      duration: 1.1,
      // expo-out easing — matches the landing's premium reveal feel
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      lerp: 0.1,
      wheelMultiplier: 1,
      touchMultiplier: 1.6,
      syncTouch: false,
    })

    // Drive Lenis from framer-motion's frame loop (time is in ms).
    const update = (data) => {
      lenis.raf(data.timestamp)
    }
    frame.update(update, true)

    return () => {
      cancelFrame(update)
      lenis.destroy()
    }
  }, [reduce])

  return null
}
