import { motion, useReducedMotion, useInView } from "framer-motion"
import { useRef } from "react"

/**
 * Supabase motion language — the `fadeInUp` scroll-reveal that runs throughout
 * the marketing page. Elements fade (opacity 0→1) and rise (y 16→0) as they
 * enter the viewport, on Supabase's exact ease `cubic-bezier(0.25,0.25,0,1)`,
 * ~0.5s, with staggered children (~0.1s steps).
 *
 * Everything here honours `prefers-reduced-motion`: when reduced, `Reveal`,
 * `RevealItem` and `FadeInUp` render their content statically (no
 * transform/opacity animation), with motion-only props stripped.
 *
 * Implementation: framer-motion `whileInView` (viewport once:true + small
 * bottom margin so reveals fire a touch before fully on-screen) + variants with
 * `staggerChildren`. Compose `Reveal` (the container) with `RevealItem` (each
 * staggered child), or use `Reveal as="..."` standalone for a single element.
 */

// Supabase's signature reveal easing + timing.
const SUPA_EASE = [0.25, 0.25, 0, 1]
const SUPA_DUR = 0.5
const SUPA_STAGGER = 0.1

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: SUPA_STAGGER, delayChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: SUPA_DUR, ease: SUPA_EASE } },
}

// Standard viewport config: reveal once, fire slightly before fully on-screen.
const VIEWPORT = { once: true, margin: "0px 0px -10% 0px" }

// framer-motion-only props that must NOT reach a plain DOM element when we render
// the static (reduced-motion) fallback — otherwise React warns about unknown
// attributes. Strip them so the reduced branch is clean.
const MOTION_PROPS = new Set([
  "variants", "initial", "animate", "exit", "whileInView", "whileHover",
  "whileTap", "whileFocus", "whileDrag", "transition", "viewport", "layout",
  "layoutId", "drag",
])
function stripMotionProps(props) {
  const out = {}
  for (const k of Object.keys(props)) {
    if (!MOTION_PROPS.has(k)) out[k] = props[k]
  }
  return out
}

/**
 * Reveal — a staggered-children container. Children should be `<RevealItem>`s.
 * When `prefers-reduced-motion`, renders a plain element (no animation).
 */
export function Reveal({ as = "div", className = "", children, viewport, ...rest }) {
  const reduce = useReducedMotion()
  const Tag = motion[as] ?? motion.div
  if (reduce) {
    const Plain = as
    return (
      <Plain className={className} {...stripMotionProps(rest)}>
        {children}
      </Plain>
    )
  }
  return (
    <Tag
      variants={containerVariants}
      initial="hidden"
      whileInView="show"
      viewport={viewport ?? VIEWPORT}
      className={className}
      {...rest}
    >
      {children}
    </Tag>
  )
}

/**
 * RevealItem — one fadeInUp child inside a `<Reveal>`. Picks up the parent's
 * stagger automatically. Static under reduced motion.
 */
export function RevealItem({ as = "div", className = "", children, ...rest }) {
  const reduce = useReducedMotion()
  const Tag = motion[as] ?? motion.div
  if (reduce) {
    const Plain = as
    return (
      <Plain className={className} {...stripMotionProps(rest)}>
        {children}
      </Plain>
    )
  }
  return (
    <Tag variants={itemVariants} className={className} {...rest}>
      {children}
    </Tag>
  )
}

/**
 * InViewAnim — toggles the `landing-anim` class on its wrapper the first time it
 * scrolls into view, which is what arms the flat CSS product-graphic animations
 * (scan sweep, bar/line growth, deal-out) defined in index.css. The CSS itself
 * collapses to the finished frame under prefers-reduced-motion, so this is safe
 * to always render; we still gate the class so animations don't run off-screen.
 *
 * Renders a plain element (no framer-motion), so it composes inside SVG/HTML
 * freely and never warns about unknown DOM props.
 */
export function InViewAnim({ as: Tag = "div", className = "", children, ...rest }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: "0px 0px -15% 0px" })
  const cls = [inView ? "landing-anim" : "", className].filter(Boolean).join(" ")
  return (
    <Tag ref={ref} className={cls} {...rest}>
      {children}
    </Tag>
  )
}

/**
 * FadeInUp — a single self-contained fadeInUp element (no parent container
 * needed). Use for one-off reveals (a lone heading, a CTA block). `delay`
 * offsets the start. Static under reduced motion.
 */
export function FadeInUp({ as = "div", className = "", children, delay = 0, y = 20, ...rest }) {
  const reduce = useReducedMotion()
  const Tag = motion[as] ?? motion.div
  if (reduce) {
    const Plain = as
    return (
      <Plain className={className} {...stripMotionProps(rest)}>
        {children}
      </Plain>
    )
  }
  return (
    <Tag
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={VIEWPORT}
      transition={{ duration: SUPA_DUR, ease: SUPA_EASE, delay }}
      className={className}
      {...rest}
    >
      {children}
    </Tag>
  )
}
