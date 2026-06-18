import { useRef } from "react"
import {
  motion,
  useScroll,
  useSpring,
  useTransform,
  useMotionValueEvent,
  useReducedMotion,
} from "framer-motion"
import { Users, ListChecks } from "lucide-react"
import BubbleSheet, { ShuffledSheet, GradedSheet } from "./BubbleSheet"
import { spring } from "./motion/tokens"

const N = 8 // unique shuffled sheets dealt in Act 2

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

// ── Act helper — 4-point bidirectional windows; overlapping = crossfade ────────
function useAct(p, [inS, inE, outS, outE]) {
  const opacity = useTransform(p, [inS, inE, outS, outE], [0, 1, 1, 0])
  const y = useTransform(p, [inS, inE, outS, outE], [40, 0, 0, -40])
  return { opacity, y }
}

// ── Act 1 — Assemble (0.00–0.25): roster + bank converge on the shuffle node ──
function Act1Assemble({ p }) {
  const { opacity, y } = useAct(p, [0.0, 0.06, 0.2, 0.25])
  const xRoster = useTransform(p, [0, 0.2], ["-34%", "-10%"])
  const xBank = useTransform(p, [0, 0.2], ["34%", "10%"])

  return (
    <motion.div style={{ opacity, y }} className="absolute inset-0 flex items-center justify-center">
      <div className="relative flex w-full max-w-3xl items-center justify-center px-4">
        <motion.div
          style={{ x: xRoster }}
          className="w-[44%] max-w-[280px] rounded-2xl border border-white/12 bg-white/[0.04] p-4 shadow-2xl backdrop-blur"
        >
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-300">
              <Users className="size-4" />
            </span>
            <p className="text-sm font-semibold text-white">Class roster</p>
          </div>
          <ul className="mt-3 space-y-1.5">
            {STUDENTS.slice(0, 4).map((s) => (
              <li key={s.roll} className="flex items-center gap-2 rounded-lg bg-white/5 px-2.5 py-1.5">
                <span className="flex size-6 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-semibold text-white">
                  {s.name[0]}
                </span>
                <span className="text-sm text-neutral-200">{s.name}</span>
                <span className="ml-auto font-mono text-xs text-neutral-400">{s.roll}</span>
              </li>
            ))}
            <li className="px-2.5 pt-0.5 text-xs text-neutral-400">+ 37 more…</li>
          </ul>
        </motion.div>

        {/* merge node */}
        <div className="relative z-10 mx-[-3%] flex size-16 shrink-0 items-center justify-center rounded-full border border-cyan-300/40 bg-cyan-300/10 text-cyan-200 backdrop-blur">
          <span className="text-[10px] font-bold uppercase tracking-wide">Shuffle</span>
        </div>

        <motion.div
          style={{ x: xBank }}
          className="w-[44%] max-w-[280px] rounded-2xl border border-white/12 bg-white/[0.04] p-4 shadow-2xl backdrop-blur"
        >
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-teal-400/20 text-teal-300">
              <ListChecks className="size-4" />
            </span>
            <p className="text-sm font-semibold text-white">Question bank</p>
          </div>
          <ul className="mt-3 space-y-2">
            {[{ q: "Capital of France?", c: "B" }, { q: "7 × 8 = ?", c: "C" }].map((item, i) => (
              <li key={i} className="rounded-lg bg-white/5 px-2.5 py-2">
                <p className="text-sm font-medium text-neutral-200">Q{i + 1}. {item.q}</p>
                <div className="mt-1.5 flex gap-1.5">
                  {["A", "B", "C", "D"].map((o) => (
                    <span
                      key={o}
                      className={[
                        "flex size-6 items-center justify-center rounded-full border text-xs",
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
function Sheet({ i, n, p }) {
  const spread = i - (n - 1) / 2 // centered: -3.5 … +3.5
  const s = 0.25 + i * 0.012 // per-card stagger so the deal blooms
  const x = useTransform(p, [s, s + 0.25], ["0%", `${spread * 58}%`])
  const y = useTransform(p, [s, s + 0.25], [0, Math.abs(spread) * 14])
  const rotate = useTransform(p, [s, s + 0.25], [0, spread * 7])
  const scale = useTransform(p, [0.25, 0.33, 0.55], [0.88, 1, 0.86])
  const opacity = useTransform(p, [s, s + 0.06], [0, 1])
  const student = STUDENTS[i % STUDENTS.length]

  return (
    <motion.div
      style={{
        x, y, rotate, scale, opacity,
        transformOrigin: "50% 120%",
        zIndex: n - Math.abs(Math.round(spread)),
      }}
      className="absolute w-[150px] will-change-transform sm:w-[168px]"
    >
      <div className="rounded-2xl border border-white/12 bg-white/[0.05] p-1.5 shadow-xl backdrop-blur">
        <div className="mb-1 flex items-center justify-between px-1.5 pt-1">
          <span className="truncate text-[11px] font-semibold text-white">{student.name}</span>
          <span
            className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-neutral-950"
            style={{ backgroundColor: student.tint }}
          >
            Shuffled
          </span>
        </div>
        <ShuffledSheet seed={i + 1} name={student.name} roll={String(101 + i)} tint={student.tint} className="aspect-[200/264]" />
      </div>
    </motion.div>
  )
}

function Act2FanOut({ p }) {
  const { opacity } = useAct(p, [0.25, 0.31, 0.5, 0.55])
  const countRef = useRef(null)
  const nMV = useTransform(p, [0.27, 0.5], [1, N])
  useMotionValueEvent(nMV, "change", (v) => {
    if (countRef.current) countRef.current.textContent = String(Math.max(1, Math.round(v)))
  })
  // merge-node pulse gated to this range
  const pulse = useTransform(p, [0.25, 0.35, 0.5], [0.4, 1, 0.5])
  const pulseScale = useTransform(p, [0.25, 0.4, 0.55], [0.9, 1.15, 1])

  return (
    <motion.div style={{ opacity }} className="absolute inset-0 flex flex-col items-center justify-center">
      <div className="relative flex h-[360px] w-full max-w-2xl items-center justify-center">
        {/* merge-node pulse behind the deck */}
        <motion.div
          aria-hidden
          style={{ opacity: pulse, scale: pulseScale }}
          className="absolute size-40 rounded-full blur-2xl"
        >
          <div className="size-full rounded-full" style={{ background: "radial-gradient(circle, rgba(56,189,248,0.45), transparent 70%)" }} />
        </motion.div>
        {Array.from({ length: N }).map((_, i) => (
          <Sheet key={i} i={i} n={N} p={p} />
        ))}
      </div>
      <p className="mt-2 text-center text-sm text-neutral-300">
        <span ref={countRef} className="text-2xl font-bold tabular-nums text-white">1</span>
        <span className="text-neutral-400"> / {N} unique sheets dealt — each with its own shuffled order &amp; private key</span>
      </p>
    </motion.div>
  )
}

// ── Act 3 — Scan & auto-grade (0.55–0.78): scan line + clipPath grade wipe ─────
function Act3Scan({ p }) {
  const { opacity, y } = useAct(p, [0.55, 0.61, 0.72, 0.78])
  const scanY = useTransform(p, [0.58, 0.74], ["0%", "100%"])
  const scanOpacity = useTransform(p, [0.56, 0.6, 0.72, 0.76], [0, 1, 1, 0])
  const clip = useTransform(p, [0.58, 0.74], ["inset(0 0 100% 0)", "inset(0 0 0% 0)"])

  return (
    <motion.div style={{ opacity, y }} className="absolute inset-0 flex items-center justify-center">
      <div className="relative w-[210px] sm:w-[230px]">
        <div className="rounded-2xl border border-white/12 bg-white/[0.04] p-2 shadow-2xl backdrop-blur">
          {/* base ungraded sheet */}
          <BubbleSheet seed={2} name="Ravi Kumar" roll="102" tint="#38bdf8" className="aspect-[200/264]" />
          {/* graded version wipes in over the base */}
          <motion.div style={{ clipPath: clip }} className="absolute inset-2">
            <GradedSheet seed={2} name="Ravi Kumar" roll="102" tint="#38bdf8" score="13/15" className="aspect-[200/264]" />
          </motion.div>
          {/* scan line */}
          <motion.div
            aria-hidden
            style={{ top: scanY, opacity: scanOpacity }}
            className="absolute inset-x-2 h-1.5 -translate-y-1/2 rounded bg-emerald-400/80 blur-[2px] shadow-[0_0_20px_2px_rgba(52,211,153,0.6)]"
          />
        </div>
        <p className="mt-4 text-center text-sm text-neutral-300">
          Scanned, aligned &amp; auto-graded against <span className="text-emerald-300">its own key</span> — unsure marks go to review, never guessed.
        </p>
      </div>
    </motion.div>
  )
}

// ── Act 4 — Analytics profile (0.78–1.00): mastery bars + score count-up ───────
function Bar({ p, from, to, target, color, label }) {
  // scaleY grows the full-height bar from its base (transform-only, perf-safe).
  const h = useTransform(p, [from, to], [0.02, target])
  return (
    <div className="flex flex-1 flex-col items-center gap-1.5">
      <div className="flex h-32 w-full items-end justify-center sm:h-40">
        <motion.div
          style={{ scaleY: h, transformOrigin: "bottom", backgroundColor: color }}
          className="h-full w-5 rounded-t-md sm:w-7"
        />
      </div>
      <span className="text-[10px] text-neutral-400">{label}</span>
    </div>
  )
}

function Act4Analytics({ p }) {
  const { opacity, y } = useAct(p, [0.78, 0.84, 1.0, 1.0])
  const scoreRef = useRef(null)
  const score = useTransform(p, [0.82, 0.96], [0, 87])
  useMotionValueEvent(score, "change", (v) => {
    if (scoreRef.current) scoreRef.current.textContent = Math.round(v) + "%"
  })

  const bars = [
    { t: 0.55, c: "#6366f1", l: "Algebra" },
    { t: 0.78, c: "#38bdf8", l: "Geometry" },
    { t: 0.92, c: "#2dd4bf", l: "Numbers" },
    { t: 0.7, c: "#34d399", l: "Fractions" },
    { t: 0.48, c: "#fbbf24", l: "Ratios" },
    { t: 0.83, c: "#a78bfa", l: "Logic" },
  ]

  return (
    <motion.div style={{ opacity, y }} className="absolute inset-0 flex items-center justify-center px-4">
      <div className="w-full max-w-xl rounded-2xl border border-white/12 bg-white/[0.04] p-5 shadow-2xl backdrop-blur sm:p-6">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">Class profile</p>
            <p className="mt-1 text-sm text-neutral-300">Per-topic mastery · overall score</p>
          </div>
          <p ref={scoreRef} className="text-4xl font-bold tabular-nums text-white sm:text-5xl">0%</p>
        </div>
        <div className="mt-5 flex items-end gap-2 sm:gap-3">
          {bars.map((b, i) => (
            <Bar key={i} p={p} from={0.82 + i * 0.01} to={0.97} target={b.t} color={b.c} label={b.l} />
          ))}
        </div>
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          <div className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm text-neutral-200">
            <span>🏆</span> Topper: <strong className="text-white">Neha Patel</strong> — 15/15
          </div>
          <div className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm text-neutral-200">
            <span>🎯</span> Hardest: <strong className="text-white">Q12</strong> — 28% correct
          </div>
        </div>
      </div>
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

// ── SVG flow spine — pathLength draws off p (connective tissue) ────────────────
function FlowConnectors({ p }) {
  const l1 = useTransform(p, [0.02, 0.2], [0, 1])
  const fanK = useTransform(p, [0.28, 0.5], [0, 1])
  const fade = useTransform(p, [0.0, 0.05, 0.52, 0.58], [0, 1, 1, 0])
  const lines = Array.from({ length: N }).map((_, i) => {
    const spread = i - (N - 1) / 2
    return `M500 480 L${500 + spread * 58} ${560 + Math.abs(spread) * 8}`
  })
  return (
    <motion.svg
      aria-hidden
      viewBox="0 0 1000 1000"
      preserveAspectRatio="xMidYMid slice"
      style={{ opacity: fade }}
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      {/* converge lines (Act 1) — solid + blurred halo copy = glow */}
      {["M180 420 L500 480", "M820 420 L500 480"].map((d, i) => (
        <g key={i}>
          <motion.path d={d} fill="none" stroke="rgba(56,189,248,0.5)" strokeWidth={6} strokeLinecap="round" strokeDasharray="0 1" style={{ pathLength: l1, filter: "blur(6px)" }} />
          <motion.path d={d} fill="none" stroke="rgba(56,189,248,0.9)" strokeWidth={2} strokeLinecap="round" strokeDasharray="0 1" style={{ pathLength: l1 }} />
        </g>
      ))}
      {/* fan lines (Act 2) */}
      {lines.map((d, i) => (
        <motion.path key={i} d={d} fill="none" stroke="rgba(99,102,241,0.7)" strokeWidth={1.6} strokeLinecap="round" strokeDasharray="0 1" style={{ pathLength: fanK }} />
      ))}
    </motion.svg>
  )
}

// ── Reduced-motion / static end-state (no sticky, no 450vh) ────────────────────
function StaticEndState() {
  return (
    <section id="how-it-works" className="mx-auto max-w-5xl px-4 py-20">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-cyan-300">How it works</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">
          From two lists to graded results
        </h2>
        <p className="mt-3 text-neutral-300">One roster · one bank · a unique sheet for every student.</p>
      </div>

      {/* labelled unique sheets */}
      <div className="mt-12 flex flex-wrap items-start justify-center gap-4">
        {STUDENTS.slice(0, 4).map((s, i) => (
          <div key={s.roll} className="w-[150px] rounded-2xl border border-white/12 bg-white/[0.05] p-1.5">
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

      {/* graded sheet + filled bars */}
      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        <div className="mx-auto w-[210px] rounded-2xl border border-white/12 bg-white/[0.04] p-2">
          <GradedSheet seed={2} name="Ravi Kumar" roll="102" tint="#38bdf8" score="13/15" className="aspect-[200/264]" />
        </div>
        <div className="rounded-2xl border border-white/12 bg-white/[0.04] p-5">
          <div className="flex items-end justify-between">
            <p className="text-sm text-neutral-300">Class profile</p>
            <p className="text-4xl font-bold text-white">87%</p>
          </div>
          <div className="mt-5 flex h-32 items-end gap-2">
            {[55, 78, 92, 70, 48, 83].map((h, i) => (
              <div key={i} className="flex-1 rounded-t-md" style={{ height: `${h}%`, backgroundColor: ["#6366f1", "#38bdf8", "#2dd4bf", "#34d399", "#fbbf24", "#a78bfa"][i] }} />
            ))}
          </div>
        </div>
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
        <FlowConnectors p={p} />
        <Act1Assemble p={p} />
        <Act2FanOut p={p} />
        <Act3Scan p={p} />
        <Act4Analytics p={p} />
      </div>
    </section>
  )
}
