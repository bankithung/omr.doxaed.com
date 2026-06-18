import { useRef } from "react"
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useMotionValueEvent,
  useReducedMotion,
} from "framer-motion"
import BubbleSheet, { ShuffledSheet, GradedSheet } from "./BubbleSheet"
import MaterialIcon from "./MaterialIcon"
import FlowSpine from "./FlowSpine"
import { AnalyticsDashboard, AnalyticsStatic } from "./Analytics"
import { spring } from "./motion/tokens"

const N = 7 // odd → one true CENTER sheet, so the fan is symmetric & balanced

const STUDENTS = [
  { name: "Asha Devi", roll: "101", tint: "#6366f1" },
  { name: "Ravi Kumar", roll: "102", tint: "#38bdf8" },
  { name: "Priya Singh", roll: "103", tint: "#2dd4bf" },
  { name: "Imran Khan", roll: "104", tint: "#34d399" },
  { name: "Neha Patel", roll: "105", tint: "#fbbf24" },
  { name: "Sara Ali", roll: "106", tint: "#fb7185" },
  { name: "Dev Mehra", roll: "107", tint: "#a78bfa" },
  { name: "Kiran Rao", roll: "108", tint: "#22d3ee" },
]

// ── Act helper — 4-point bidirectional windows; tight handoff (no double-exposure)
// Returns opacity + lift + visibility/z gating so only the ACTIVE act is shown,
// interactive, and on top. `visibility:hidden` once fully faded guarantees a
// faded act can never bleed through or overlap the next one.
function useAct(p, [inS, inE, outS, outE]) {
  const opacity = useTransform(p, [inS, inE, outS, outE], [0, 1, 1, 0])
  const y = useTransform(p, [inS, inE, outS, outE], [30, 0, 0, -30])
  // active strictly between the fade-in midpoint and fade-out midpoint
  const visibility = useTransform(p, (v) => (v > inS - 0.001 && v < outE + 0.001 ? "visible" : "hidden"))
  const zIndex = useTransform(p, (v) => (v >= inE && v <= outS ? 20 : 10))
  const pointerEvents = "none" // whole stage is non-interactive (decorative)
  return { opacity, y, visibility, zIndex, pointerEvents }
}

// Shared stage frame: every act centers inside ONE viewport, never overflowing.
// max-h/max-w keep content within the sticky h-screen stage at all sizes.
const STAGE = "absolute inset-0 flex items-center justify-center px-4 sm:px-6"
const STAGE_INNER = "flex max-h-[86vh] w-full max-w-[min(1200px,92vw)] flex-col items-center justify-center"

// ── Act 1 — Assemble (visible from p=0): roster + bank converge on the node ────
function Act1Assemble({ p }) {
  // window starts at 0 so the section NEVER opens on a black frame
  const { opacity, y, visibility, zIndex } = useAct(p, [0.0, 0.0, 0.2, 0.25])
  const xRoster = useTransform(p, [0, 0.2], ["-30%", "-9%"])
  const xBank = useTransform(p, [0, 0.2], ["30%", "9%"])

  return (
    <motion.div style={{ opacity, y, visibility, zIndex }} className={STAGE}>
      <div className="relative flex max-h-[86vh] w-full max-w-[min(1100px,92vw)] items-center justify-center gap-1 sm:gap-2">
        <motion.div style={{ x: xRoster }} className="glass w-[46%] max-w-[420px] rounded-2xl p-3.5 sm:p-5 lg:p-6">
          <div className="flex items-center gap-2 sm:gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-300 sm:size-10">
              <MaterialIcon name="groups" className="size-[18px] sm:size-5" />
            </span>
            <p className="text-sm font-semibold text-white sm:text-lg">Class roster</p>
          </div>
          <ul className="mt-3 space-y-1.5 sm:mt-4 sm:space-y-2.5">
            {STUDENTS.slice(0, 5).map((s) => (
              <li key={s.roll} className="flex items-center gap-2 rounded-lg bg-white/5 px-2.5 py-1.5 sm:gap-3 sm:px-3 sm:py-2.5">
                <span className="flex size-6 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-semibold text-white sm:size-8 sm:text-sm">
                  {s.name[0]}
                </span>
                <span className="truncate text-sm text-neutral-200 sm:text-base">{s.name}</span>
                <span className="ml-auto font-mono-data text-xs text-neutral-400 sm:text-sm">{s.roll}</span>
              </li>
            ))}
            <li className="px-2.5 pt-0.5 font-mono-data text-xs text-neutral-400 sm:text-sm">+ 36 more…</li>
          </ul>
        </motion.div>

        {/* merge node */}
        <div className="glass relative z-10 mx-[-2.5%] flex size-14 shrink-0 items-center justify-center rounded-full border-cyan-300/40 text-cyan-200 sm:size-20">
          <MaterialIcon name="shuffle" className="size-5 sm:size-7" />
        </div>

        <motion.div style={{ x: xBank }} className="glass w-[46%] max-w-[420px] rounded-2xl p-3.5 sm:p-5 lg:p-6">
          <div className="flex items-center gap-2 sm:gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-teal-400/20 text-teal-300 sm:size-10">
              <MaterialIcon name="checklist" className="size-[18px] sm:size-5" />
            </span>
            <p className="text-sm font-semibold text-white sm:text-lg">Question bank</p>
          </div>
          <ul className="mt-3 space-y-2 sm:mt-4 sm:space-y-3">
            {[{ q: "Capital of France?", c: "B" }, { q: "7 × 8 = ?", c: "C" }].map((item, i) => (
              <li key={i} className="rounded-lg bg-white/5 px-2.5 py-2 sm:px-3.5 sm:py-3">
                <p className="text-sm font-medium text-neutral-200 sm:text-base">Q{i + 1}. {item.q}</p>
                <div className="mt-1.5 flex gap-1.5 sm:mt-2.5 sm:gap-2">
                  {["A", "B", "C", "D"].map((o) => (
                    <span
                      key={o}
                      className={[
                        "flex size-6 items-center justify-center rounded-full border text-xs sm:size-8 sm:text-sm",
                        o === item.c ? "border-teal-300 bg-teal-400/20 text-teal-200" : "border-white/15 text-neutral-400",
                      ].join(" ")}
                    >
                      {o}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </motion.div>
      </div>
    </motion.div>
  )
}

// ── Act 2 — FAN-OUT (0.25–0.55): deck deals into N unique shuffled sheets ──────
// Badge restaging: the FRONT sheet (centre of the fan) carries one prominent
// "Shuffled" pill; every other sheet gets only a subtle tinted depth dot whose
// strength falls off with distance from centre — so the fan reads cleanly at
// every scrub position instead of a pile of competing pills.
function Sheet({ i, n, p }) {
  const spread = i - (n - 1) / 2 // symmetric about centre: e.g. -3 … +3 (n=7)
  const depth = Math.abs(spread) // 0 (front/centre) … (n-1)/2 (back)
  const isFront = depth < 0.5 // exactly the centre sheet on odd n
  const s = 0.27 + i * 0.012 // per-card stagger so the deal blooms (within Act 2)
  // spread in VIEWPORT WIDTH units (vw) so the fan scales with the screen and
  // never clips on mobile — symmetric about centre so the fan stays centred.
  const x = useTransform(p, [s, s + 0.22], ["0vw", `${spread * 9}vw`])
  const y = useTransform(p, [s, s + 0.22], [0, depth * depth * 4])
  const rotate = useTransform(p, [s, s + 0.22], [0, spread * 6])
  const scale = useTransform(p, [0.27, 0.36, 0.54], [0.9, 1, 0.9])
  const opacity = useTransform(p, [s, s + 0.05], [0, 1])
  // back sheets recede slightly so the front reads as the hero card
  const dim = useTransform(p, [s + 0.08, s + 0.22], [0, isFront ? 0 : Math.min(0.3, depth * 0.08)])
  const student = STUDENTS[i % STUDENTS.length]

  return (
    // Outer wrapper fills the stage and CENTERS the sheet (flex), so the fan is
    // symmetric about the true centre. The inner motion sheet fans out from there
    // (a bare `absolute` sheet would anchor to its top-left static position and
    // make the whole fan drift left — the bug this fixes).
    <div
      className="absolute inset-0 flex items-center justify-center"
      style={{ zIndex: n - Math.round(depth) }}
    >
      <motion.div
        style={{ x, y, rotate, scale, opacity, transformOrigin: "50% 100%" }}
        className="w-[clamp(138px,30vw,260px)] will-change-transform"
      >
        <div className="glass relative rounded-2xl p-1.5 sm:p-2">
          <div className="mb-1 flex items-center justify-between gap-1 px-1.5 pt-1">
            <span className="truncate text-[11px] font-semibold text-white sm:text-xs">{student.name}</span>
            {isFront ? (
              <span
                className="shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-neutral-950 sm:text-[10px]"
                style={{ backgroundColor: student.tint }}
              >
                Shuffled
              </span>
            ) : (
              <span
                aria-hidden
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: student.tint, opacity: 0.85 }}
              />
            )}
          </div>
          <ShuffledSheet seed={i + 1} name={student.name} roll={String(101 + i)} tint={student.tint} className="aspect-[200/264]" />
          {/* depth dimmer — fades back sheets so the front card pops */}
          <motion.div aria-hidden style={{ opacity: dim }} className="pointer-events-none absolute inset-0 rounded-2xl bg-[#05060a]" />
        </div>
      </motion.div>
    </div>
  )
}

function Act2FanOut({ p }) {
  const { opacity, visibility, zIndex } = useAct(p, [0.24, 0.3, 0.52, 0.56])
  const countRef = useRef(null)
  const nMV = useTransform(p, [0.3, 0.5], [1, N])
  useMotionValueEvent(nMV, "change", (v) => {
    if (countRef.current) countRef.current.textContent = String(Math.max(1, Math.round(v)))
  })
  // merge-node pulse gated to this range
  const pulse = useTransform(p, [0.26, 0.36, 0.52], [0.4, 1, 0.5])
  const pulseScale = useTransform(p, [0.26, 0.4, 0.54], [0.9, 1.15, 1])

  return (
    <motion.div style={{ opacity, visibility, zIndex }} className={[STAGE, "flex-col"].join(" ")}>
      <div className={STAGE_INNER}>
        {/* fan stage — fixed-ratio box centred in the viewport; sheets fan symmetrically */}
        <div className="relative flex h-[clamp(300px,56vh,560px)] w-full items-center justify-center">
          {/* merge-node pulse behind the deck */}
          <motion.div
            aria-hidden
            style={{ opacity: pulse, scale: pulseScale }}
            className="absolute size-[clamp(180px,38vmin,320px)] rounded-full blur-2xl"
          >
            <div className="size-full rounded-full" style={{ background: "radial-gradient(circle, rgba(56,189,248,0.45), transparent 70%)" }} />
          </motion.div>
          {Array.from({ length: N }).map((_, i) => (
            <Sheet key={i} i={i} n={N} p={p} />
          ))}
        </div>
        <p className="mt-4 max-w-[640px] text-center text-sm text-neutral-300 sm:text-base">
          <span ref={countRef} className="font-mono-data text-2xl font-semibold text-white sm:text-3xl">1</span>
          <span className="font-mono-data text-neutral-400"> / {N}</span>
          <span className="text-neutral-400"> </span>
          <span className="font-serif-accent text-lg text-cyan-200 sm:text-xl">unique</span>
          <span className="text-neutral-400"> sheets dealt — each with its own shuffled order &amp; private key</span>
        </p>
      </div>
    </motion.div>
  )
}

// ── Act 3 — Scan & auto-grade a BATCH: a stack tossed across the desk. Sheets
// SCATTER over the stage with varied offsets + rotations; each gets its own
// scan-line sweep + staggered grade wipe. ─────────────────────────────────────
// pos = % offset from centre (x,y), rot = deg. Tuned so the spread fits the
// stage at every size while reading as several distinct, scattered sheets.
const SCAN_BATCH = [
  { seed: 4, name: "Imran Khan", roll: "104", tint: "#34d399", score: "12/15", pos: [-30, -14], rot: -11 },
  { seed: 3, name: "Priya Singh", roll: "103", tint: "#2dd4bf", score: "14/15", pos: [28, -18], rot: 9 },
  { seed: 5, name: "Neha Patel", roll: "105", tint: "#fbbf24", score: "15/15", pos: [32, 16], rot: 7 },
  { seed: 2, name: "Ravi Kumar", roll: "102", tint: "#38bdf8", score: "13/15", pos: [-4, 6], rot: -2 }, // hero, front+centre
]

function ScanSheet({ item, idx, total, p }) {
  // grade in staggered slices of Act 3; the front/hero sheet (last) leads
  const order = total - 1 - idx // 0 for the front hero sheet … up for the scattered ones
  const a = 0.59 + order * 0.026
  const b = a + 0.08
  const clip = useTransform(p, [a, b], ["inset(0 0 100% 0)", "inset(0 0 0% 0)"])
  const scanY = useTransform(p, [a, b], ["0%", "100%"])
  const scanOpacity = useTransform(p, [a - 0.012, a + 0.012, b - 0.012, b + 0.012], [0, 1, 1, 0])
  const isHero = idx === total - 1
  return (
    <div
      className={[
        "absolute left-1/2 top-1/2 w-[clamp(150px,40vmin,300px)] rounded-2xl p-2 sm:p-2.5",
        isHero ? "glass-strong" : "glass",
      ].join(" ")}
      style={{
        transform: `translate(-50%, -50%) translate(${item.pos[0]}%, ${item.pos[1]}%) rotate(${item.rot}deg)`,
        zIndex: 10 + idx,
      }}
    >
      <BubbleSheet seed={item.seed} name={item.name} roll={item.roll} tint={item.tint} className="aspect-[200/264]" />
      <motion.div style={{ clipPath: clip }} className="absolute inset-2 sm:inset-2.5">
        <GradedSheet seed={item.seed} name={item.name} roll={item.roll} tint={item.tint} score={item.score} className="aspect-[200/264]" />
      </motion.div>
      {/* each sheet sweeps its own scan line as it grades */}
      <motion.div
        aria-hidden
        style={{ top: scanY, opacity: scanOpacity }}
        className="absolute inset-x-2 h-1.5 -translate-y-1/2 rounded bg-emerald-400/80 blur-[2px] shadow-[0_0_20px_2px_rgba(52,211,153,0.6)] sm:inset-x-2.5"
      />
    </div>
  )
}

function Act3Scan({ p }) {
  const { opacity, y, visibility, zIndex } = useAct(p, [0.56, 0.62, 0.72, 0.78])

  return (
    <motion.div style={{ opacity, y, visibility, zIndex }} className={[STAGE, "flex-col"].join(" ")}>
      <div className={STAGE_INNER}>
        {/* the scattered batch — sheets spread across the stage, each scanned */}
        <div className="relative h-[clamp(320px,60vh,560px)] w-full">
          {SCAN_BATCH.map((item, idx) => (
            <ScanSheet key={item.seed} item={item} idx={idx} total={SCAN_BATCH.length} p={p} />
          ))}
        </div>
        <p className="mx-auto mt-4 max-w-[460px] text-center text-sm text-neutral-300 sm:text-base">
          A whole stack scanned, aligned &amp; auto-graded against{" "}
          <span className="font-serif-accent text-base text-emerald-300 sm:text-lg">its own key</span> — unsure marks go to review, never guessed.
        </p>
      </div>
    </motion.div>
  )
}

// ── Act 4 — God-tier analytics (0.78–1.00): the dashboard ASSEMBLES off `p`. ────
// The viz live in Analytics.jsx; this act only frames + reveals the panel.
function Act4Analytics({ p }) {
  const { opacity, y, visibility, zIndex } = useAct(p, [0.76, 0.82, 1.0, 1.0])

  return (
    <motion.div style={{ opacity, y, visibility, zIndex }} className={STAGE}>
      <AnalyticsDashboard p={p} />
    </motion.div>
  )
}

// ── Parallax backdrop inside the pin (texture drifts off the same p) ───────────
function ParallaxBackdrop({ p }) {
  const yBg = useTransform(p, [0, 1], ["0%", "12%"])
  return (
    <motion.div
      aria-hidden
      style={{ y: yBg }}
      className="pointer-events-none absolute inset-0"
    >
      <div
        className="absolute inset-0 opacity-60"
        style={{
          backgroundImage:
            "radial-gradient(circle, transparent 1.5px, rgba(255,255,255,0.05) 1.5px, rgba(255,255,255,0.05) 2.5px, transparent 2.5px)",
          backgroundSize: "30px 30px",
          WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, #000 40%, transparent)",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, #000 40%, transparent)",
        }}
      />
    </motion.div>
  )
}

// ── Reduced-motion / static end-state (no sticky, no 450vh) ────────────────────
function StaticEndState() {
  return (
    <section id="how-it-works" className="mx-auto max-w-5xl px-4 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <p className="font-mono-data text-xs font-medium uppercase tracking-[0.18em] text-cyan-300">How it works</p>
        <h2 className="text-display-sm mt-3 text-3xl font-semibold text-white sm:text-4xl">
          From two lists to graded results
        </h2>
        <p className="mt-3 text-neutral-300">
          One roster · one bank · a <span className="font-serif-accent text-xl text-cyan-200">unique</span> sheet for every student.
        </p>
      </div>

      {/* labelled unique sheets */}
      <div className="mt-12 flex flex-wrap items-start justify-center gap-4">
        {STUDENTS.slice(0, 4).map((s, i) => (
          <div key={s.roll} className="glass w-[150px] rounded-2xl p-1.5">
            <div className="mb-1 flex items-center justify-between px-1.5 pt-1">
              <span className="truncate text-[11px] font-semibold text-white">{s.name}</span>
              <span className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase text-neutral-950" style={{ backgroundColor: s.tint }}>
                Shuffled
              </span>
            </div>
            <ShuffledSheet seed={i + 1} name={s.name} roll={s.roll} tint={s.tint} className="aspect-[200/264]" />
          </div>
        ))}
      </div>

      {/* graded sheet + the assembled analytics dashboard (static end-state) */}
      <div className="mt-10 grid items-start gap-6 lg:grid-cols-[210px_1fr]">
        <div className="glass-strong mx-auto w-[210px] rounded-2xl p-2">
          <GradedSheet seed={2} name="Ravi Kumar" roll="102" tint="#38bdf8" score="13/15" className="aspect-[200/264]" />
        </div>
        <AnalyticsStatic />
      </div>
    </section>
  )
}

// ── The pinned shell — ONE tall section, sticky stage, one spring-smoothed p ───
export default function Centerpiece() {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] })
  const p = useSpring(scrollYProgress, spring.scroll)

  if (reduce) return <StaticEndState />

  return (
    <section
      ref={ref}
      id="how-it-works"
      data-scrolljack
      className="relative h-[450vh]"
    >
      <div className="sticky top-0 flex h-screen items-center justify-center overflow-hidden">
        <ParallaxBackdrop p={p} />
        <FlowSpine p={p} n={N} />
        <Act1Assemble p={p} />
        <Act2FanOut p={p} />
        <Act3Scan p={p} />
        <Act4Analytics p={p} />
      </div>
    </section>
  )
}
