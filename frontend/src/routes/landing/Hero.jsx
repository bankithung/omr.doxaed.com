import { useRef } from "react"
import { Link } from "react-router-dom"
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useReducedMotion,
} from "framer-motion"
import { ArrowRight, Sparkles } from "lucide-react"
import { KineticHeadline, MagneticButton } from "./Micro"
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
  if (reduce) {
    return <p className="mt-6 max-w-xl text-balance text-lg text-neutral-300 sm:text-xl">{SUBLINE}</p>
  }
  return (
    <motion.p
      variants={parent}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: false, amount: 0.6 }}
      className="mt-6 max-w-xl text-balance text-lg text-neutral-300 sm:text-xl"
    >
      {words.map((w, i) => {
        const accent = w === "unique" || w === "sheet"
        return (
          <motion.span
            key={`${w}-${i}`}
            variants={child}
            className={["inline-block", accent ? "font-semibold text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-teal-300" : ""].join(" ")}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        )
      })}
    </motion.p>
  )
}

// Animated aurora bloom behind the hero (grade-band palette, mirror loop).
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
    <motion.div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10"
      initial={{ opacity: 0 }}
      animate={{
        opacity: 1,
        background: [
          "radial-gradient(55% 45% at 30% 10%, rgba(99,102,241,0.30), transparent 70%), radial-gradient(45% 40% at 75% 20%, rgba(45,212,191,0.22), transparent 70%)",
          "radial-gradient(55% 45% at 70% 5%, rgba(56,189,248,0.26), transparent 70%), radial-gradient(45% 40% at 25% 25%, rgba(251,113,133,0.16), transparent 70%)",
          "radial-gradient(55% 45% at 30% 10%, rgba(99,102,241,0.30), transparent 70%), radial-gradient(45% 40% at 75% 20%, rgba(45,212,191,0.22), transparent 70%)",
        ],
      }}
      transition={{
        opacity: { duration: 1 },
        background: { duration: 16, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" },
      }}
    />
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
    <section ref={ref} className="relative flex min-h-screen items-center overflow-hidden px-4 pt-28 pb-16 sm:pt-32">
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

      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div style={headStyle}>
          <motion.span
            initial={reduce ? false : { opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.6 }}
            transition={{ duration: dur.enter, ease: ease.out }}
            className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-neutral-200 backdrop-blur"
          >
            <Sparkles className="size-3.5 text-cyan-300" />
            Generate · Scan · Auto-grade · Analyse
          </motion.span>

          <KineticHeadline
            text={HEADLINE}
            accentWords={["minutes"]}
            accentClassName="text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-cyan-300 to-teal-300"
            className="mt-6 text-balance text-4xl font-bold leading-[1.04] tracking-tight text-white sm:text-6xl lg:text-7xl"
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
                className="inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-white px-6 text-base font-semibold text-neutral-950 shadow-[0_0_44px_-8px_rgba(99,102,241,0.85)] transition-colors hover:bg-neutral-100"
              >
                Start free <ArrowRight className="size-4" />
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
            className="mt-5 text-xs text-neutral-400"
          >
            No card required · Works with any phone or scanner · Built for tutors, coaching centres & schools
          </motion.p>
        </motion.div>

        {/* master OMR sheet — lifts and hands off to the pinned centerpiece below */}
        <motion.div
          style={sheetStyle}
          initial={reduce ? false : { opacity: 0, y: 36, scale: 0.94 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: ease.outSoft, delay: 0.2 }}
          className="relative mx-auto w-full max-w-[300px] sm:max-w-[340px]"
        >
          <div
            className="absolute -inset-6 -z-10 rounded-[2rem] blur-2xl"
            style={{ background: "radial-gradient(circle, rgba(99,102,241,0.40), transparent 70%)" }}
          />
          <div className="rounded-3xl border border-white/12 bg-white/[0.04] p-3 shadow-2xl backdrop-blur">
            <BubbleSheet seed={7} name="Asha Devi" roll="101" tint="#6366f1" className="aspect-[200/264]" />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
