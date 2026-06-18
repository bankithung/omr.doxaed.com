import {
  motion,
  useMotionValue,
  useMotionTemplate,
  useReducedMotion,
} from "framer-motion"
import MaterialIcon from "./MaterialIcon"
import { usePointerFine } from "./Micro"
import { ease, dur, stagger } from "./motion/tokens"

const FEATURES = [
  { icon: "shuffle", title: "Per-student shuffle", body: "Question and option order shuffled uniquely per student; every sheet stores its own answer key so grading stays exact.", span: "sm:col-span-2 sm:row-span-2", big: true },
  { icon: "groups", title: "Roster-native", body: "Start from a class list — name students or just pick a count." },
  { icon: "checklist", title: "One question bank", body: "Write MCQs once; reuse across tests and sections." },
  { icon: "scan", title: "Scan from any device", body: "Phone, scanner, or a stack of photos — auto-aligned by fiducials + QR." },
  { icon: "shield", title: "Never guessed", body: "Faint, double-marked or missing reads go to a review queue — not a guess." },
  { icon: "analytics", title: "Analytics profile", body: "Distributions, toppers, hardest questions, per-student improvement over time." },
]

const container = { hidden: {}, show: { transition: { staggerChildren: stagger.base, delayChildren: 0.05 } } }
const item = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: dur.enter, ease: ease.out } },
}

export default function Bento() {
  const fine = usePointerFine()
  const reduce = useReducedMotion()
  const mx = useMotionValue(-9999)
  const my = useMotionValue(-9999)
  const spotlight = useMotionTemplate`radial-gradient(380px circle at ${mx}px ${my}px, rgba(99,102,241,0.16), transparent 78%)`
  const active = fine && !reduce

  function onMove(e) {
    const r = e.currentTarget.getBoundingClientRect()
    mx.set(e.clientX - r.left)
    my.set(e.clientY - r.top)
  }
  function onLeave() {
    mx.set(-9999)
    my.set(-9999)
  }

  return (
    <section id="features" className="px-4 py-24 sm:px-6 sm:py-32">
      <div className="mx-auto max-w-2xl text-center">
        <p className="font-mono-data text-xs font-medium uppercase tracking-[0.18em] text-cyan-300">Why DoxaEd OMR</p>
        <h2 className="text-display-sm mt-3 text-3xl font-semibold text-white sm:text-[2.6rem]">
          Everything you need to grade <span className="font-serif-accent text-[1.15em] text-cyan-200">faster</span> — and{" "}
          <span className="font-serif-accent text-[1.15em] text-cyan-200">fairer</span>
        </h2>
      </div>

      <motion.div
        onMouseMove={active ? onMove : undefined}
        onMouseLeave={active ? onLeave : undefined}
        variants={container}
        initial="hidden"
        whileInView="show"
        viewport={{ once: false, amount: 0.2, margin: "0px 0px -10% 0px" }}
        className="group relative mx-auto mt-12 grid max-w-5xl grid-cols-1 gap-3 sm:grid-cols-3"
      >
        {/* shared cursor spotlight across the whole grid */}
        {active && (
          <motion.div
            aria-hidden
            style={{ background: spotlight }}
            className="pointer-events-none absolute inset-0 z-0 rounded-3xl"
          />
        )}

        {FEATURES.map(({ icon, title, body, span, big }) => (
          <motion.div
            key={title}
            variants={item}
            whileHover={active ? { y: -4 } : undefined}
            transition={{ type: "spring", stiffness: 300, damping: 22 }}
            className={[
              "group/tile glass relative z-10 overflow-hidden rounded-2xl p-5",
              span ?? "",
            ].join(" ")}
          >
            <span className="flex size-10 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300">
              <MaterialIcon name={icon} className="size-[22px]" />
            </span>
            <div className="mt-4 flex items-start justify-between gap-3">
              <h3 className={["font-semibold text-white", big ? "text-xl" : "text-lg"].join(" ")}>{title}</h3>
              <MaterialIcon name="arrow" className="size-4 shrink-0 -translate-x-1 -rotate-45 text-neutral-500 opacity-0 transition-all duration-200 group-hover/tile:translate-x-0 group-hover/tile:opacity-100" />
            </div>
            <p className={["mt-1.5 text-neutral-300", big ? "text-base" : "text-sm"].join(" ")}>{body}</p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  )
}
