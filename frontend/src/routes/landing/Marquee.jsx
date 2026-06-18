import {
  motion,
  useScroll,
  useSpring,
  useVelocity,
  useTransform,
  useReducedMotion,
} from "framer-motion"

const ROW_A = ["Sunrise Coaching", "Vidya Academy", "St. Xavier's", "BrightMinds Tutorials", "Apex Learning", "Nalanda Institute", "Crescent School"]
const ROW_B = ["Per-student shuffle", "Anti-cheat", "1-tap scan", "Item analysis", "Per-student profile", "Review queue", "Public results"]

function Track({ items, reverse }) {
  return (
    <div className="flex w-max animate-none">
      <ul className={["flex shrink-0 items-center gap-10 px-5", reverse ? "marquee-rev" : "marquee"].join(" ")}>
        {items.map((t, i) => (
          <li key={i} className="whitespace-nowrap text-lg font-medium text-neutral-300">
            {t}
            <span className="ml-10 text-cyan-400/50">•</span>
          </li>
        ))}
      </ul>
      <ul aria-hidden className={["flex shrink-0 items-center gap-10 px-5", reverse ? "marquee-rev" : "marquee"].join(" ")}>
        {items.map((t, i) => (
          <li key={i} className="whitespace-nowrap text-lg font-medium text-neutral-300">
            {t}
            <span className="ml-10 text-cyan-400/50">•</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Marquee() {
  const reduce = useReducedMotion()
  const { scrollY } = useScroll()
  const velocity = useVelocity(scrollY)
  const smooth = useSpring(velocity, { stiffness: 300, damping: 50 })
  const skew = useTransform(smooth, [-2000, 0, 2000], ["-4deg", "0deg", "4deg"], { clamp: true })

  return (
    <section className="overflow-hidden border-y border-white/10 py-12">
      <p className="mb-6 text-center text-xs font-medium uppercase tracking-wider text-neutral-500">
        Trusted by teachers at tutoring centres &amp; schools
      </p>
      <motion.div
        style={reduce ? undefined : { skewY: skew }}
        className="flex flex-col gap-5 [mask-image:linear-gradient(to_right,transparent,#000_12%,#000_88%,transparent)]"
      >
        <Track items={ROW_A} reverse={false} />
        <Track items={ROW_B} reverse />
      </motion.div>
    </section>
  )
}
