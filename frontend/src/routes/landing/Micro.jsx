import { useEffect, useRef, useState } from "react"
import {
  motion,
  useMotionValue,
  useMotionTemplate,
  useMotionValueEvent,
  useSpring,
  useTransform,
  useInView,
  useReducedMotion,
} from "framer-motion"
import { ease, spring, dur, stagger } from "./motion/tokens"

// ── usePointerFine — gate pointer effects to real cursors (storyboard §4) ──────
export function usePointerFine() {
  const [fine, setFine] = useState(false)
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return
    const mq = window.matchMedia("(hover: hover) and (pointer: fine)")
    const update = () => setFine(mq.matches)
    update()
    mq.addEventListener?.("change", update)
    return () => mq.removeEventListener?.("change", update)
  }, [])
  return fine
}

// ── MagneticButton — leans toward the cursor; inner label leads (parallax-in) ──
export function MagneticButton({
  children,
  strength = 0.35,
  labelStrength = 0.6,
  className = "",
  ...rest
}) {
  const ref = useRef(null)
  const fine = usePointerFine()
  const reduce = useReducedMotion()
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const lx = useMotionValue(0)
  const ly = useMotionValue(0)
  const sx = useSpring(x, spring.snappy)
  const sy = useSpring(y, spring.snappy)
  const slx = useSpring(lx, spring.snappy)
  const sly = useSpring(ly, spring.snappy)

  const active = fine && !reduce

  function onMove(e) {
    if (!active || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    const dx = e.clientX - (r.left + r.width / 2)
    const dy = e.clientY - (r.top + r.height / 2)
    x.set(dx * strength)
    y.set(dy * strength)
    lx.set(dx * labelStrength)
    ly.set(dy * labelStrength)
  }
  function reset() {
    x.set(0)
    y.set(0)
    lx.set(0)
    ly.set(0)
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={active ? { x: sx, y: sy } : undefined}
      className={["inline-flex p-3", className].join(" ")}
      {...rest}
    >
      <motion.span style={active ? { x: slx, y: sly } : undefined} className="contents">
        {children}
      </motion.span>
    </motion.div>
  )
}

// ── TiltCard — 3D tilt with a glare sheen that tracks the cursor ───────────────
export function TiltCard({ children, className = "", max = 8, glare = true }) {
  const ref = useRef(null)
  const fine = usePointerFine()
  const reduce = useReducedMotion()
  const active = fine && !reduce

  const rx = useMotionValue(0)
  const ry = useMotionValue(0)
  const sprx = useSpring(rx, spring.smooth)
  const spry = useSpring(ry, spring.smooth)
  const rotateX = useTransform(sprx, [-0.5, 0.5], [`${max}deg`, `${-max}deg`])
  const rotateY = useTransform(spry, [-0.5, 0.5], [`${-max}deg`, `${max}deg`])
  const gx = useTransform(spry, [-0.5, 0.5], ["0%", "100%"])
  const gy = useTransform(sprx, [-0.5, 0.5], ["0%", "100%"])
  const glareBg = useMotionTemplate`radial-gradient(circle at ${gx} ${gy}, rgba(255,255,255,0.28), transparent 45%)`

  function onMove(e) {
    if (!active || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    rx.set((e.clientY - r.top) / r.height - 0.5)
    ry.set((e.clientX - r.left) / r.width - 0.5)
  }
  function reset() {
    rx.set(0)
    ry.set(0)
  }

  if (!active) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      className={["relative [perspective:1000px]", className].join(" ")}
    >
      {children}
      {glare && (
        <motion.div
          aria-hidden
          style={{ background: glareBg }}
          className="pointer-events-none absolute inset-0 rounded-[inherit]"
        />
      )}
    </motion.div>
  )
}

// ── CountUp — number tickers that REPLAY on scroll-up (no once:true) ────────────
export function CountUp({
  to,
  from = 0,
  suffix = "",
  prefix = "",
  decimals = 0,
  className = "",
  format = false,
}) {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const inView = useInView(ref, { once: false, margin: "-50px" })
  const mv = useSpring(from, { mass: 0.8, stiffness: 75, damping: 15 })

  useEffect(() => {
    if (reduce) {
      mv.jump(to)
      return
    }
    mv.set(inView ? to : from)
  }, [inView, to, from, reduce, mv])

  useMotionValueEvent(mv, "change", (v) => {
    if (!ref.current) return
    const n = decimals ? v.toFixed(decimals) : Math.round(v)
    ref.current.textContent =
      prefix + (format ? Intl.NumberFormat("en-US").format(Math.round(v)) : n) + suffix
  })

  return (
    <span ref={ref} className={className}>
      {prefix}
      {decimals ? Number(from).toFixed(decimals) : from}
      {suffix}
    </span>
  )
}

// ── KineticHeadline — masked word reveal, bidirectional, a11y-correct ──────────
// The <h1> carries the accessible name via aria-label; animated spans are aria-hidden.
export function KineticHeadline({
  text,
  as = "h1",
  className = "",
  accentWords = [],
  accentClassName = "",
  amount = 0.6,
  id,
}) {
  const reduce = useReducedMotion()
  const Tag = motion[as] ?? motion.h1
  const words = text.split(" ")

  const parent = {
    hidden: {},
    visible: { transition: { staggerChildren: stagger.words } },
  }
  const child = {
    hidden: { y: "115%" },
    visible: { y: 0, transition: { duration: dur.hero, ease: ease.out } },
  }

  if (reduce) {
    const Static = as
    return (
      <Static id={id} className={className}>
        {text}
      </Static>
    )
  }

  return (
    <Tag
      id={id}
      aria-label={text}
      className={className}
      variants={parent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: false, amount }}
    >
      {words.map((w, i) => {
        const accent = accentWords.includes(w.replace(/[.,]/g, ""))
        return (
          <span
            key={`${w}-${i}`}
            aria-hidden="true"
            className="inline-block overflow-hidden pb-[0.12em] align-bottom"
          >
            <motion.span
              variants={child}
              className={["inline-block", accent ? accentClassName : ""].join(" ")}
            >
              {w}
              {i < words.length - 1 ? " " : ""}
            </motion.span>
          </span>
        )
      })}
    </Tag>
  )
}
