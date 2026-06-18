import { useRef } from "react"
import { Link } from "react-router-dom"
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useReducedMotion,
} from "framer-motion"
import { KineticHeadline, MagneticButton } from "./Micro"
import MaterialIcon from "./MaterialIcon"
import BubbleSheet from "./BubbleSheet"
import { ease, dur, stagger } from "./motion/tokens"

// E2E CONTRACT: the <h1> accessible name must match /Grade a stack of bubble sheets/.
// KineticHeadline puts the full text in aria-label and marks animated spans aria-hidden.
const HEADLINE = "Grade a stack of bubble sheets in minutes."
const SUBLINE = "One bank. One roster. A unique sheet for every student."

// Animated sub-headline: word-by-word fade-up, accent on "unique sheet".
function SubHeadline() {
  const reduce = useReducedMotion()
  const words = SUBLINE.split(" ")
  const parent = { hidden: {}, visible: { transition: { staggerChildren: stagger.base, delayChildren: 0.45 } } }
  const child = {
    hidden: { opacity: 0, y: 14 },
    visible: { opacity: 1, y: 0, transition: { duration: dur.enter, ease: ease.out } },
  }
  // Serif-italic accent on "unique" — the signature expensive move.
  const isAccent = (w) => w.replace(/[.,]/g, "") === "unique"
  if (reduce) {
    return (
      <p className="mt-7 max-w-xl text-balance text-lg leading-relaxed text-neutral-300 sm:text-xl">
        {words.map((w, i) => (
          <span key={`${w}-${i}`} className={isAccent(w) ? "font-serif-accent text-2xl text-cyan-200 sm:text-[1.6rem]" : ""}>
            {w}
            {i < words.length - 1 ? " " : ""}
          </span>
        ))}
      </p>
    )
  }
  return (
    <motion.p
      variants={parent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: false, amount: 0.6 }}
      className="mt-7 max-w-xl text-balance text-lg leading-relaxed text-neutral-300 sm:text-xl"
    >
      {words.map((w, i) => {
        const accent = isAccent(w)
        return (
          <motion.span
            key={`${w}-${i}`}
            variants={child}
            className={["inline-block", accent ? "font-serif-accent text-2xl text-cyan-200 sm:text-[1.6rem]" : ""].join(" ")}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        )
      })}
    </motion.p>
  )
}

// Deep multi-layer aurora behind the hero. Two independently drifting blob
// layers (different speeds/phases) give real parallax depth; a third static
// spotlight anchors the top. Grade-band palette: indigo / teal / cyan / rose.
function Aurora() {
  const reduce = useReducedMotion()
  if (reduce) {
    return (
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: "radial-gradient(60% 50% at 50% 0%, rgba(99,102,241,0.22), transparent 70%)" }}
      />
    )
  }
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      {/* anchored top spotlight */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(70% 55% at 50% -8%, rgba(99,102,241,0.28), transparent 68%)" }}
      />
      {/* slow indigo/teal layer */}
      <motion.div
        className="absolute inset-0 blur-2xl"
        initial={{ opacity: 0 }}
        animate={{
          opacity: 1,
          background: [
            "radial-gradient(48% 42% at 24% 18%, rgba(99,102,241,0.34), transparent 70%), radial-gradient(42% 38% at 78% 24%, rgba(45,212,191,0.24), transparent 70%)",
            "radial-gradient(48% 42% at 70% 8%, rgba(79,70,229,0.30), transparent 70%), radial-gradient(42% 38% at 22% 30%, rgba(56,189,248,0.22), transparent 70%)",
            "radial-gradient(48% 42% at 24% 18%, rgba(99,102,241,0.34), transparent 70%), radial-gradient(42% 38% at 78% 24%, rgba(45,212,191,0.24), transparent 70%)",
          ],
        }}
        transition={{
          opacity: { duration: 1.2 },
          background: { duration: 22, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" },
        }}
      />
      {/* faster grade-band shimmer (cyan/rose), offset phase for parallax */}
      <motion.div
        className="absolute inset-0 blur-3xl mix-blend-screen"
        initial={{ opacity: 0 }}
        animate={{
          opacity: 0.9,
          background: [
            "radial-gradient(40% 34% at 60% 30%, rgba(56,189,248,0.18), transparent 72%), radial-gradient(34% 30% at 32% 12%, rgba(251,113,133,0.12), transparent 72%)",
            "radial-gradient(40% 34% at 34% 22%, rgba(45,212,191,0.16), transparent 72%), radial-gradient(34% 30% at 72% 20%, rgba(99,102,241,0.16), transparent 72%)",
            "radial-gradient(40% 34% at 60% 30%, rgba(56,189,248,0.18), transparent 72%), radial-gradient(34% 30% at 32% 12%, rgba(251,113,133,0.12), transparent 72%)",
          ],
        }}
        transition={{
          opacity: { duration: 1.4 },
          background: { duration: 14, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" },
        }}
      />
    </div>
  )
}

export default function Hero() {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] })
  const p = useSpring(scrollYProgress, { stiffness: 90, damping: 30, restDelta: 0.001, mass: 0.4 })

  const yBg = useTransform(p, [0, 1], ["0%", "15%"])
  const gridOpacity = useTransform(p, [0, 0.8], [1, 0])
  const ySheet = useTransform(p, [0, 1], ["0%", "-14%"])
  const yHead = useTransform(p, [0, 1], ["0%", "-5%"])
  const sheetRot = useTransform(p, [0, 1], [-5, -1])

  const headStyle = reduce ? undefined : { y: yHead }
  const sheetStyle = reduce ? { rotate: -5 } : { y: ySheet, rotate: sheetRot }

  return (
    <section ref={ref} className="relative flex min-h-screen items-center overflow-hidden px-4 pt-28 pb-16 sm:px-6 sm:pt-32 lg:px-10">
      <Aurora />

      {/* masked OMR-bubble grid field */}
      <motion.div
        aria-hidden
        style={reduce ? undefined : { y: yBg, opacity: gridOpacity }}
        className="pointer-events-none absolute inset-0 -z-10"
      >
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(circle, transparent 1.5px, rgba(255,255,255,0.07) 1.5px, rgba(255,255,255,0.07) 2.5px, transparent 2.5px)",
            backgroundSize: "26px 26px",
            WebkitMaskImage: "radial-gradient(ellipse 65% 55% at 50% 8%, #000 45%, transparent)",
            maskImage: "radial-gradient(ellipse 65% 55% at 50% 8%, #000 45%, transparent)",
          }}
        />
      </motion.div>

      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:max-w-7xl lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
        <motion.div style={headStyle}>
          <motion.span
            initial={reduce ? false : { opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.6 }}
            transition={{ duration: dur.enter, ease: ease.out }}
            className="glass inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-neutral-200"
          >
            <MaterialIcon name="sparkles" className="size-3.5 text-cyan-300" />
            <span className="font-mono-data tracking-[0.16em]">Generate · Scan · Grade · Analyse</span>
          </motion.span>

          <KineticHeadline
            text={HEADLINE}
            accentWords={["minutes"]}
            accentClassName="font-serif-accent font-normal tracking-normal text-cyan-200"
            className="text-display mt-7 text-balance font-semibold text-white text-[clamp(2.3rem,7.5vw,5.25rem)]"
          />

          <SubHeadline />

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.5 }}
            transition={{ duration: dur.enter, ease: ease.out, delay: 0.55 }}
            className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center"
          >
            <MagneticButton className="p-1.5">
              <Link
                to="/register"
                className="group inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-white px-6 text-base font-semibold text-neutral-950 shadow-[0_0_44px_-8px_rgba(99,102,241,0.85)] transition-colors hover:bg-neutral-100"
              >
                Start free
                <MaterialIcon name="arrow" className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
              </Link>
            </MagneticButton>
            <Link
              to="/login"
              className="inline-flex min-h-[48px] items-center justify-center rounded-xl border border-white/15 px-6 text-base font-medium text-neutral-200 transition-colors hover:border-white/30 hover:text-white"
            >
              Sign in
            </Link>
          </motion.div>

          <motion.p
            initial={reduce ? false : { opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: false }}
            transition={{ duration: dur.enter, delay: 0.7 }}
            className="mt-6 text-xs text-neutral-400"
          >
            <span className="font-mono-data">No card required</span> · Works with any phone or scanner · Built for
            tutors, coaching centres &amp; schools
          </motion.p>
        </motion.div>

        {/* master OMR sheet — lifts and hands off to the pinned centerpiece below */}
        <motion.div
          style={sheetStyle}
          initial={reduce ? false : { opacity: 0, y: 36, scale: 0.94 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: ease.outSoft, delay: 0.2 }}
          className="relative mx-auto w-full max-w-[300px] sm:max-w-[340px] lg:max-w-[400px]"
        >
          <div
            className="absolute -inset-8 -z-10 rounded-[2.25rem] blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(99,102,241,0.42), rgba(45,212,191,0.14) 55%, transparent 72%)" }}
          />
          <div className="glass-strong rounded-[1.75rem] p-3">
            <BubbleSheet seed={7} name="Asha Devi" roll="101" tint="#6366f1" className="aspect-[200/264]" />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
