import { useEffect, useRef, useState } from "react"
import { motion, useInView, useReducedMotion } from "framer-motion"

// Shared easing — a soft "out-expo"-ish curve for premium reveals.
export const EASE = [0.22, 1, 0.36, 1]

/**
 * Reveal — fades + lifts its children into view once, on scroll.
 * Respects prefers-reduced-motion (renders statically).
 */
export function Reveal({
  children,
  className,
  delay = 0,
  y = 28,
  once = true,
  as = "div",
}) {
  const reduce = useReducedMotion()
  const Comp = motion[as] ?? motion.div
  if (reduce) {
    const Static = as
    return <Static className={className}>{children}</Static>
  }
  return (
    <Comp
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, margin: "-70px" }}
      transition={{ duration: 0.65, delay, ease: EASE }}
    >
      {children}
    </Comp>
  )
}

/**
 * Stagger — a container whose direct Reveal/motion children animate in sequence.
 */
export function Stagger({ children, className, gap = 0.09, once = true }) {
  const reduce = useReducedMotion()
  if (reduce) return <div className={className}>{children}</div>
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once, margin: "-70px" }}
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: gap } },
      }}
    >
      {children}
    </motion.div>
  )
}

export const staggerItem = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE } },
}

/**
 * CountUp — animates a number from 0 → `to` when it scrolls into view.
 */
export function CountUp({ to, suffix = "", prefix = "", decimals = 0, duration = 1.5 }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: "-50px" })
  const reduce = useReducedMotion()
  const [val, setVal] = useState(reduce ? to : 0)

  useEffect(() => {
    if (!inView || reduce) return
    let raf
    let start
    const tick = (t) => {
      if (start === undefined) start = t
      const p = Math.min((t - start) / (duration * 1000), 1)
      const eased = 1 - Math.pow(1 - p, 3)
      setVal(to * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, to, duration, reduce])

  return (
    <span ref={ref}>
      {prefix}
      {val.toFixed(decimals)}
      {suffix}
    </span>
  )
}
