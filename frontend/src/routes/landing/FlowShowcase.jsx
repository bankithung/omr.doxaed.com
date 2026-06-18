import { useRef } from "react"
import { motion, useScroll, useReducedMotion } from "framer-motion"
import { Users, ListChecks, Sparkles, ScanLine, BarChart3, Check } from "lucide-react"
import BubbleSheet from "./BubbleSheet"
import { Reveal, Stagger, staggerItem, CountUp, EASE } from "./Primitives"

const STUDENTS = [
  { name: "Asha Devi", roll: "101" },
  { name: "Ravi Kumar", roll: "102" },
  { name: "Priya Singh", roll: "103" },
  { name: "Imran Khan", roll: "104" },
  { name: "Neha Patel", roll: "105" },
]

// ── Act 1: the two inputs ─────────────────────────────────────────────────────
function InputsVisual() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Reveal className="rounded-2xl border bg-card p-4 shadow-sm" y={20}>
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Users className="size-4" />
          </span>
          <p className="text-sm font-semibold">Class roster</p>
          <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            41 students
          </span>
        </div>
        <ul className="mt-3 space-y-1.5">
          {STUDENTS.slice(0, 4).map((s) => (
            <li key={s.roll} className="flex items-center gap-2 rounded-lg bg-muted/50 px-2.5 py-1.5">
              <span className="flex size-6 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                {s.name[0]}
              </span>
              <span className="text-sm">{s.name}</span>
              <span className="ml-auto font-mono text-xs text-muted-foreground">{s.roll}</span>
            </li>
          ))}
          <li className="px-2.5 pt-0.5 text-xs text-muted-foreground">+ 37 more…</li>
        </ul>
      </Reveal>

      <Reveal className="rounded-2xl border bg-card p-4 shadow-sm" y={20} delay={0.1}>
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <ListChecks className="size-4" />
          </span>
          <p className="text-sm font-semibold">Question bank</p>
          <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            50 MCQs
          </span>
        </div>
        <ul className="mt-3 space-y-2">
          {[
            { q: "Capital of France?", correct: "B" },
            { q: "7 × 8 = ?", correct: "C" },
          ].map((item, i) => (
            <li key={i} className="rounded-lg bg-muted/50 px-2.5 py-2">
              <p className="text-sm font-medium">Q{i + 1}. {item.q}</p>
              <div className="mt-1.5 flex gap-1.5">
                {["A", "B", "C", "D"].map((o) => (
                  <span
                    key={o}
                    className={[
                      "flex size-6 items-center justify-center rounded-full border text-xs",
                      o === item.correct
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border text-muted-foreground",
                    ].join(" ")}
                  >
                    {o}
                  </span>
                ))}
                <span className="ml-1 flex items-center text-xs text-primary">
                  <Check className="size-3.5" /> key set
                </span>
              </div>
            </li>
          ))}
        </ul>
      </Reveal>
    </div>
  )
}

// ── Act 2: the shuffled fan-out (the centerpiece) ─────────────────────────────
const FAN = [
  { name: "Asha Devi", roll: "101", answers: [1, 2, 0, 3, 1, 0, 2], tint: "var(--chart-1)", rot: -10, x: -116, z: 10 },
  { name: "Ravi Kumar", roll: "102", answers: [0, 3, 2, 1, 0, 2, 3], tint: "var(--chart-3)", rot: 0, x: 0, z: 30 },
  { name: "Priya Singh", roll: "103", answers: [2, 0, 3, 0, 2, 1, 1], tint: "var(--chart-4)", rot: 10, x: 116, z: 20 },
]

function FanVisual() {
  const reduce = useReducedMotion()
  return (
    <div className="relative mx-auto flex h-[330px] w-full max-w-md items-center justify-center sm:h-[360px]">
      {FAN.map((s, i) => (
        <motion.div
          key={s.roll}
          className="absolute w-[150px] rounded-2xl border bg-card p-1.5 shadow-xl sm:w-[176px]"
          style={{ zIndex: s.z }}
          initial={reduce ? false : { x: 0, rotate: 0, y: 30, opacity: 0, scale: 0.9 }}
          whileInView={{ x: s.x * 0.62, rotate: s.rot, y: 0, opacity: 1, scale: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, delay: 0.12 * i, ease: EASE }}
        >
          <div className="mb-1 flex items-center justify-between px-1.5 pt-1">
            <span className="truncate text-[11px] font-semibold">{s.name}</span>
            <span
              className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-primary-foreground"
              style={{ backgroundColor: s.tint }}
            >
              Shuffled
            </span>
          </div>
          <BubbleSheet
            name={s.name}
            roll={s.roll}
            answers={s.answers}
            tint={s.tint}
            className="aspect-[200/264]"
          />
        </motion.div>
      ))}
    </div>
  )
}

// ── Act 3: scan + auto-grade ──────────────────────────────────────────────────
function ScanVisual() {
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-stretch">
      <Reveal className="mx-auto w-[180px] shrink-0 rounded-2xl border bg-card p-2 shadow-xl">
        <BubbleSheet
          name="Ravi Kumar"
          roll="102"
          answers={[0, 3, 2, 1, 0, 2, 3]}
          tint="var(--chart-3)"
          scanning
          graded
          score="13/15"
          className="aspect-[200/264]"
        />
      </Reveal>
      <div className="flex flex-1 flex-col justify-center gap-2.5">
        {[
          { c: "var(--chart-4)", t: "Sheet detected & aligned by fiducials + QR" },
          { c: "var(--chart-3)", t: "Bubbles read, multi-page sheets auto-stitched" },
          { c: "var(--chart-1)", t: "Graded against this sheet's own answer key" },
          { c: "var(--chart-2)", t: "Unsure marks → review queue, never guessed" },
        ].map((row, i) => (
          <Reveal key={i} delay={0.08 * i} className="flex items-center gap-2.5 rounded-xl border bg-card px-3 py-2 shadow-sm">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-full text-primary-foreground"
              style={{ backgroundColor: row.c }}>
              <Check className="size-3.5" />
            </span>
            <span className="text-sm">{row.t}</span>
          </Reveal>
        ))}
      </div>
    </div>
  )
}

// ── Act 4: analytics profile ──────────────────────────────────────────────────
const BARS = [38, 55, 72, 90, 76, 58, 44]
function AnalyticsVisual() {
  const reduce = useReducedMotion()
  return (
    <div className="rounded-2xl border bg-card p-5 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Class average", to: 71, suffix: "%" },
          { label: "Students graded", to: 41, suffix: "" },
          { label: "Test reliability", to: 0.82, suffix: "", decimals: 2 },
        ].map((s) => (
          <div key={s.label} className="rounded-xl bg-muted/50 px-3 py-3">
            <p className="text-2xl font-bold tabular-nums">
              <CountUp to={s.to} suffix={s.suffix} decimals={s.decimals ?? 0} />
            </p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>

      {/* score distribution */}
      <p className="mt-5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Score distribution
      </p>
      <div className="mt-2 flex h-28 items-end gap-2">
        {BARS.map((h, i) => (
          <motion.div
            key={i}
            className="flex-1 rounded-t-md"
            style={{
              height: `${h}%`,
              backgroundColor: `var(--chart-${(i % 5) + 1})`,
              transformOrigin: "bottom",
            }}
            initial={reduce ? false : { scaleY: 0 }}
            whileInView={{ scaleY: 1 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.7, delay: 0.06 * i, ease: EASE }}
          />
        ))}
      </div>

      <Stagger className="mt-4 grid gap-2 sm:grid-cols-2" gap={0.1}>
        <motion.div variants={staggerItem} className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2">
          <span className="text-base">🏆</span>
          <span className="text-sm">Topper: <strong>Neha Patel</strong> — 15/15</span>
        </motion.div>
        <motion.div variants={staggerItem} className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2">
          <span className="text-base">🎯</span>
          <span className="text-sm">Hardest: <strong>Q12</strong> — 28% correct</span>
        </motion.div>
      </Stagger>
    </div>
  )
}

// ── Acts data ─────────────────────────────────────────────────────────────────
const ACTS = [
  {
    icon: Users,
    kicker: "Step 1",
    title: "Start with what you already have",
    copy: "One class roster and one bank of MCQs. No per-student setup — name them or just pick a count.",
    Visual: InputsVisual,
  },
  {
    icon: Sparkles,
    kicker: "Step 2",
    title: "One click → a unique sheet for every student",
    copy: "OMRFlow shuffles question and option order per student, pre-bubbles each roll number, and bakes a private answer key into every sheet — so copying a neighbour gets you nowhere. Need it? You also get each student's shuffled question paper.",
    Visual: FanVisual,
  },
  {
    icon: ScanLine,
    kicker: "Step 3",
    title: "Scan the stack — grading happens itself",
    copy: "Feed photos or a scanner from any device. Each sheet is auto-aligned, read, and graded against its own key. Whatever it can't read for sure goes to review, never a guess.",
    Visual: ScanVisual,
  },
  {
    icon: BarChart3,
    kicker: "Step 4",
    title: "Every test becomes an analytics profile",
    copy: "Score distributions, toppers, the hardest questions, per-student improvement across retests — and a shareable public result link anyone can look up by roll number.",
    Visual: AnalyticsVisual,
  },
]

export default function FlowShowcase() {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.35", "end 0.65"],
  })

  return (
    <section id="how-it-works" className="mx-auto max-w-5xl px-4 py-20 sm:py-28">
      <Reveal className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-primary">How it works</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          From two lists to graded results — watch it flow
        </h2>
        <p className="mt-3 text-muted-foreground">
          The whole loop, top to bottom. Scroll through it.
        </p>
      </Reveal>

      <div ref={ref} className="relative mt-14">
        {/* timeline rail (desktop) */}
        <div className="pointer-events-none absolute bottom-0 left-[19px] top-2 hidden w-0.5 bg-border sm:block">
          {!reduce && (
            <motion.div
              className="absolute inset-x-0 top-0 origin-top bg-primary"
              style={{ scaleY: scrollYProgress, height: "100%" }}
            />
          )}
        </div>

        <div className="space-y-16 sm:space-y-24">
          {ACTS.map((act, i) => {
            const Icon = act.icon
            const Visual = act.Visual
            return (
              <div key={i} className="relative sm:pl-16">
                {/* marker */}
                <div className="mb-4 flex items-center gap-3 sm:absolute sm:left-0 sm:top-0 sm:mb-0">
                  <span className="relative z-10 flex size-10 items-center justify-center rounded-full border-2 border-primary bg-background text-primary shadow-sm">
                    <Icon className="size-5" />
                  </span>
                  <span className="text-sm font-semibold text-primary sm:hidden">{act.kicker}</span>
                </div>

                <Reveal className="max-w-2xl">
                  <p className="hidden text-sm font-semibold uppercase tracking-wide text-primary sm:block">
                    {act.kicker}
                  </p>
                  <h3 className="mt-1 text-xl font-bold sm:text-2xl">{act.title}</h3>
                  <p className="mt-2 text-muted-foreground">{act.copy}</p>
                </Reveal>

                <div className="mt-6">
                  <Visual />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
