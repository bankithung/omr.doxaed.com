import {
  motion,
  useScroll,
  useSpring,
  useVelocity,
  useTransform,
  useReducedMotion,
} from "framer-motion"
import MaterialIcon from "./MaterialIcon"

/**
 * Trust strip — HONEST product facts only.
 *
 * We have no real customers yet, so there are NO invented schools, fake
 * testimonials, or fabricated user counts here. Instead: a quiet capability
 * strip of real, verifiable product facts, plus a keyword marquee of actual
 * features. Every claim maps to something the product genuinely does.
 */

// Real capabilities (icon + label). No social proof, no numbers we can't back.
const CAPABILITIES = [
  { icon: "shuffle", label: "6 OMR modes" },
  { icon: "target", label: "Per-student shuffle" },
  { icon: "shield", label: "Server-side grading" },
  { icon: "task", label: "Review queue — never guessed" },
  { icon: "folder", label: "Folders & sharing" },
  { icon: "lock", label: "Encrypted student PII" },
  { icon: "devices", label: "Any phone or scanner" },
  { icon: "checklist", label: "Auditable results" },
]

// Real feature keywords for the moving marquee (no brand names).
const KEYWORDS = [
  "Per-student shuffle",
  "Anti-cheat ordering",
  "1-tap scan",
  "Item analysis",
  "Per-student profile",
  "Review queue",
  "Folders & sharing",
  "Encrypted PII",
]

function Track({ items, reverse }) {
  return (
    <div className="flex w-max">
      {[0, 1].map((dup) => (
        <ul
          key={dup}
          aria-hidden={dup === 1 || undefined}
          className={["flex shrink-0 items-center gap-10 px-5", reverse ? "marquee-rev" : "marquee"].join(" ")}
        >
          {items.map((t, i) => (
            <li key={i} className="whitespace-nowrap text-base font-medium text-neutral-300">
              {t}
              <span className="ml-10 text-cyan-400/45">•</span>
            </li>
          ))}
        </ul>
      ))}
    </div>
  )
}

export default function Marquee() {
  const reduce = useReducedMotion()
  const { scrollY } = useScroll()
  const velocity = useVelocity(scrollY)
  const smooth = useSpring(velocity, { stiffness: 300, damping: 50 })
  const skew = useTransform(smooth, [-2000, 0, 2000], ["-3deg", "0deg", "3deg"], { clamp: true })

  return (
    <section className="border-y border-white/10 py-14">
      <p className="mb-8 text-center font-mono-data text-[11px] font-medium uppercase tracking-[0.18em] text-neutral-500">
        What you actually get — no fine print
      </p>

      {/* honest capability strip (static, real facts) */}
      <div className="mx-auto mb-10 grid max-w-5xl grid-cols-2 gap-2.5 px-4 sm:grid-cols-4">
        {CAPABILITIES.map((c) => (
          <div key={c.label} className="glass flex items-center gap-2.5 rounded-xl px-3 py-2.5">
            <MaterialIcon name={c.icon} className="size-4 shrink-0 text-cyan-300" />
            <span className="text-[13px] font-medium text-neutral-200">{c.label}</span>
          </div>
        ))}
      </div>

      {/* real feature-keyword marquee (motion only; no brand/customer names) */}
      <div className="overflow-hidden">
        <motion.div
          style={reduce ? undefined : { skewY: skew }}
          className="[mask-image:linear-gradient(to_right,transparent,#000_12%,#000_88%,transparent)]"
        >
          <Track items={KEYWORDS} reverse={false} />
        </motion.div>
      </div>
    </section>
  )
}
