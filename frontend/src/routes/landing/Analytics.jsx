import { useRef } from "react"
import { motion, useTransform, useMotionValueEvent } from "framer-motion"
import MaterialIcon from "./MaterialIcon"

/**
 * Analytics — Act 4 of the pinned centerpiece (scroll window ~0.78–1.00).
 *
 * A dashboard that ASSEMBLES as the shared spring progress `p` advances through
 * Act 4: a radial score gauge, a per-topic radar, a score-distribution histogram
 * under a drawn-on bell curve, a test→retest trend line with a travelling dot,
 * and a percentile track. Everything is scrubbed bidirectionally off `p` using
 * only transform / opacity / clipPath / pathLength — no layout-driving props.
 *
 * The data is illustrative (a sample class profile), labelled as such so it reads
 * as an honest product preview, not a real customer's numbers.
 *
 * Brand spectrum (chart-1..5 + grade bands): indigo #6366f1, cyan #38bdf8,
 * teal #2dd4bf, emerald #34d399, amber #fbbf24, violet #a78bfa, rose #fb7185.
 */

// ── small helper: map a sub-window of Act 4 to [0,1] for a viz's reveal ────────
const win = (a, b) => [a, b]

// ── Radial score gauge — a 270° arc sweeps + a tabular number ticks up ─────────
function ScoreGauge({ p }) {
  const ref = useRef(null)
  // 270° sweep arc; r=52, circumference of full = 2πr; arc spans 0.75 of it.
  const R = 52
  const CIRC = 2 * Math.PI * R
  const ARC = CIRC * 0.75
  // draw the stroke 0→full across the gauge reveal window
  const draw = useTransform(p, win(0.82, 0.95), [0, 1])
  const dashOffset = useTransform(draw, (v) => ARC * (1 - v * (87 / 100)))
  const glowOpacity = useTransform(p, [0.82, 0.9, 1], [0, 1, 1])
  const score = useTransform(p, win(0.83, 0.96), [0, 87])
  useMotionValueEvent(score, "change", (v) => {
    if (ref.current) ref.current.textContent = Math.round(v)
  })

  return (
    <div className="relative flex flex-col items-center">
      <svg viewBox="0 0 140 140" className="w-36 sm:w-40 lg:w-44" aria-hidden>
        {/* track */}
        <circle
          cx="70" cy="70" r={R} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="9"
          strokeLinecap="round" strokeDasharray={`${ARC} ${CIRC}`}
          transform="rotate(135 70 70)"
        />
        {/* glow under-stroke */}
        <motion.circle
          cx="70" cy="70" r={R} fill="none" stroke="url(#gaugeGrad)" strokeWidth="13"
          strokeLinecap="round" strokeDasharray={`${ARC} ${CIRC}`}
          strokeDashoffset={dashOffset} transform="rotate(135 70 70)"
          style={{ filter: "blur(6px)", opacity: glowOpacity }}
        />
        {/* main stroke */}
        <motion.circle
          cx="70" cy="70" r={R} fill="none" stroke="url(#gaugeGrad)" strokeWidth="9"
          strokeLinecap="round" strokeDasharray={`${ARC} ${CIRC}`}
          strokeDashoffset={dashOffset} transform="rotate(135 70 70)"
        />
        <defs>
          <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="55%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="flex items-baseline font-mono-data text-[2.75rem] font-semibold leading-none text-white sm:text-5xl lg:text-[3.25rem]">
          <span ref={ref}>0</span>
          <span className="ml-0.5 text-2xl text-neutral-400">%</span>
        </span>
        <span className="mt-1 text-[10px] font-medium uppercase tracking-[0.16em] text-neutral-400 sm:text-[11px]">
          Class avg
        </span>
      </div>
    </div>
  )
}

// ── Per-topic radar — polygon draws from centre & fills; axis labels fade in ───
const RADAR = [
  { label: "Algebra", v: 0.86 },
  { label: "Geometry", v: 0.72 },
  { label: "Numbers", v: 0.93 },
  { label: "Fractions", v: 0.64 },
  { label: "Ratios", v: 0.78 },
  { label: "Logic", v: 0.81 },
]
function radarPoint(i, n, r, cx = 80, cy = 80) {
  const a = (Math.PI * 2 * i) / n - Math.PI / 2
  return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]
}
function Radar({ p }) {
  const n = RADAR.length
  const maxR = 58
  // grow the data polygon from the centre
  const grow = useTransform(p, win(0.86, 0.96), [0, 1])
  const scale = useTransform(grow, [0, 1], [0.001, 1])
  const fillOpacity = useTransform(p, [0.86, 0.94], [0, 0.55])
  const labelOpacity = useTransform(p, [0.9, 0.98], [0, 1])

  const polygon = RADAR.map((d, i) => radarPoint(i, n, d.v * maxR).join(",")).join(" ")
  const rings = [0.33, 0.66, 1]

  return (
    <div className="relative">
      <svg viewBox="0 0 160 160" className="w-full" aria-hidden>
        {/* grid rings */}
        {rings.map((rr, i) => (
          <polygon
            key={i}
            points={RADAR.map((_, j) => radarPoint(j, n, rr * maxR).join(",")).join(" ")}
            fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1"
          />
        ))}
        {/* spokes */}
        {RADAR.map((_, i) => {
          const [x, y] = radarPoint(i, n, maxR)
          return <line key={i} x1="80" y1="80" x2={x} y2={y} stroke="rgba(255,255,255,0.07)" strokeWidth="1" />
        })}
        {/* data polygon — scales up from centre */}
        <motion.polygon
          points={polygon}
          fill="rgba(56,189,248,0.18)"
          stroke="#38bdf8"
          strokeWidth="1.6"
          strokeLinejoin="round"
          style={{ scale, transformOrigin: "80px 80px", fillOpacity }}
        />
        {/* vertex dots */}
        {RADAR.map((d, i) => {
          const [x, y] = radarPoint(i, n, d.v * maxR)
          return (
            <motion.circle key={i} cx={x} cy={y} r="2.4" fill="#7dd3fc"
              style={{ scale, transformOrigin: "80px 80px", opacity: fillOpacity }} />
          )
        })}
      </svg>
      {/* axis labels — absolutely placed, fade in */}
      {RADAR.map((d, i) => {
        const [x, y] = radarPoint(i, n, maxR + 14, 50, 50)
        return (
          <motion.span
            key={d.label}
            style={{ left: `${x}%`, top: `${y}%`, opacity: labelOpacity }}
            className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap text-[9px] font-medium text-neutral-400"
          >
            {d.label}
          </motion.span>
        )
      })}
    </div>
  )
}

// ── Score distribution — bars spring up under a bell curve that draws on ───────
const DIST = [4, 9, 16, 27, 34, 28, 19, 11, 6] // illustrative counts per band
const DIST_MAX = Math.max(...DIST)

// One histogram bar (own component so the scrub hook isn't called in a loop).
function DistBar({ p, i, count }) {
  const target = count / DIST_MAX
  const h = useTransform(p, win(0.88 + i * 0.004, 0.97), [0.02, target])
  const peak = i === 4
  return (
    <motion.div
      aria-hidden
      style={{ scaleY: h, transformOrigin: "bottom" }}
      className={["flex-1 rounded-t-[3px]", peak ? "bg-cyan-400" : "bg-indigo-500/55"].join(" ")}
    />
  )
}

function Distribution({ p }) {
  const drawCurve = useTransform(p, win(0.9, 0.99), [0, 1])
  // smooth bell path across the same 9 bands (cubic through the tops)
  const W = 220
  const H = 70
  const step = W / (DIST.length - 1)
  const pts = DIST.map((c, i) => [i * step, H - (c / DIST_MAX) * (H - 6) - 3])
  let bell = `M ${pts[0][0]} ${pts[0][1]}`
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]
    const [x1, y1] = pts[i]
    const cx = (x0 + x1) / 2
    bell += ` C ${cx} ${y0}, ${cx} ${y1}, ${x1} ${y1}`
  }

  return (
    <div>
      <div className="relative h-[88px] w-full">
        {/* bars */}
        <div className="absolute inset-x-0 bottom-0 flex h-[70px] items-end gap-[3px]">
          {DIST.map((c, i) => (
            <DistBar key={i} p={p} i={i} count={c} />
          ))}
        </div>
        {/* bell curve draws on over the bars */}
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="absolute inset-x-0 bottom-[18px] h-[70px] w-full" aria-hidden>
          <motion.path
            d={bell} fill="none" stroke="#7dd3fc" strokeWidth="2"
            strokeLinecap="round" style={{ pathLength: drawCurve }}
          />
          <motion.path
            d={bell} fill="none" stroke="#38bdf8" strokeWidth="5"
            strokeLinecap="round" style={{ pathLength: drawCurve, filter: "blur(4px)", opacity: 0.5 }}
          />
        </svg>
      </div>
      <p className="mt-1 text-center text-[10px] text-neutral-500">Score distribution · 110 sheets</p>
    </div>
  )
}

// ── Test → retest trend — line draws via pathLength + travelling glowing dot ───
const TREND = [58, 61, 67, 72, 79, 87]
function Trend({ p }) {
  const W = 240
  const H = 84
  const stepX = W / (TREND.length - 1)
  const pts = TREND.map((v, i) => [i * stepX, H - ((v - 50) / 45) * (H - 10) - 5])
  let line = `M ${pts[0][0]} ${pts[0][1]}`
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]
    const [x1, y1] = pts[i]
    const cx = (x0 + x1) / 2
    line += ` C ${cx} ${y0}, ${cx} ${y1}, ${x1} ${y1}`
  }
  const area = `${line} L ${W} ${H} L 0 ${H} Z`

  const draw = useTransform(p, win(0.86, 0.98), [0, 1])
  const areaOpacity = useTransform(p, [0.9, 0.99], [0, 1])
  // travelling dot rides the polyline by interpolating across the raw points
  const dotX = useTransform(draw, [0, 1], [pts[0][0], pts[pts.length - 1][0]])
  const dotY = useTransform(draw, (v) => {
    const seg = v * (TREND.length - 1)
    const i = Math.min(TREND.length - 2, Math.floor(seg))
    const f = seg - i
    return pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
  })

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-hidden>
      <defs>
        <linearGradient id="trendArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(52,211,153,0.35)" />
          <stop offset="100%" stopColor="rgba(52,211,153,0)" />
        </linearGradient>
      </defs>
      {/* soft area fill */}
      <motion.path d={area} fill="url(#trendArea)" style={{ opacity: areaOpacity }} />
      {/* glow under-line */}
      <motion.path d={line} fill="none" stroke="#34d399" strokeWidth="6"
        strokeLinecap="round" style={{ pathLength: draw, filter: "blur(5px)", opacity: 0.5 }} />
      {/* main line */}
      <motion.path d={line} fill="none" stroke="#34d399" strokeWidth="2.4"
        strokeLinecap="round" style={{ pathLength: draw }} />
      {/* travelling dot */}
      <motion.circle r="4.5" fill="#bbf7d0" cx={dotX} cy={dotY}
        style={{ filter: "drop-shadow(0 0 6px rgba(52,211,153,0.9))" }} />
      <motion.circle r="9" fill="none" stroke="rgba(52,211,153,0.5)" strokeWidth="1.5"
        cx={dotX} cy={dotY} style={{ opacity: areaOpacity }} />
    </svg>
  )
}

// ── Percentile track — a marker slides to position + a mono number ticks up ────
function Percentile({ p }) {
  const ref = useRef(null)
  const pct = 92
  const fill = useTransform(p, win(0.88, 0.98), ["2%", `${pct}%`])
  const markerLeft = useTransform(p, win(0.88, 0.98), ["0%", `${pct}%`])
  const val = useTransform(p, win(0.88, 0.98), [0, pct])
  useMotionValueEvent(val, "change", (v) => {
    if (ref.current) ref.current.textContent = Math.round(v)
  })

  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-neutral-400">Cohort percentile</span>
        <span className="font-mono-data text-sm font-semibold text-emerald-300">
          <span ref={ref}>0</span>th
        </span>
      </div>
      <div className="relative mt-2 h-2 rounded-full bg-white/8">
        <motion.div
          style={{ width: fill }}
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400"
        />
        <motion.div
          style={{ left: markerLeft }}
          className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-emerald-400 shadow-[0_0_12px_2px_rgba(52,211,153,0.7)]"
        />
      </div>
    </div>
  )
}

// ── Stat tile — mono tabular counter that ticks to a target ────────────────────
function StatTile({ p, from, to, value, suffix = "", label, icon, accent, delay = 0 }) {
  const ref = useRef(null)
  const mv = useTransform(p, win(from + delay, to), [0, value])
  useMotionValueEvent(mv, "change", (v) => {
    if (ref.current) ref.current.textContent = (Math.round(v * 10) / 10).toFixed(value % 1 ? 1 : 0)
  })
  const opacity = useTransform(p, [from + delay, from + delay + 0.04], [0, 1])
  return (
    <motion.div style={{ opacity }} className="glass rounded-xl px-3 py-3 sm:px-4 sm:py-3.5">
      <div className="flex items-center gap-1.5 text-neutral-400">
        <MaterialIcon name={icon} className={["size-4", accent].join(" ")} />
        <span className="text-[10px] font-medium uppercase tracking-[0.12em] sm:text-[11px]">{label}</span>
      </div>
      <p className="mt-1.5 font-mono-data text-2xl font-semibold text-white sm:text-[1.75rem]">
        <span ref={ref}>0</span>
        <span className="text-base text-neutral-400">{suffix}</span>
      </p>
    </motion.div>
  )
}

// ── reveal helper (proper custom hook: opacity + lift keyed off Act-4 progress) ─
function useReveal(p, a) {
  const opacity = useTransform(p, [a, a + 0.03], [0, 1])
  const y = useTransform(p, [a, a + 0.05], [22, 0])
  return { opacity, y }
}

const SECTION_LABEL = "text-[11px] sm:text-xs font-medium uppercase tracking-[0.14em] text-neutral-400"

// ── The assembled Act-4 dashboard — full-width, fluid, reflowing grid ──────────
export function AnalyticsDashboard({ p }) {
  // called a fixed number of times in a fixed order → rules-of-hooks safe
  const headR = useReveal(p, 0.79)
  const gaugeR = useReveal(p, 0.8)
  const radarR = useReveal(p, 0.84)
  const trendR = useReveal(p, 0.85)
  const distR = useReveal(p, 0.87)
  const pctR = useReveal(p, 0.9)

  return (
    <div className="glass-strong flex max-h-[88vh] w-full max-w-[min(1180px,94vw)] flex-col rounded-[1.5rem] p-3.5 sm:p-5 lg:p-6">
      {/* header — honest "sample" label, not a real customer */}
      <motion.div style={headR} className="flex shrink-0 items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <span className="flex size-9 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300 sm:size-11">
            <MaterialIcon name="analytics" className="size-5 sm:size-6" />
          </span>
          <div>
            <p className="text-base font-semibold text-white sm:text-lg">Class analytics</p>
            <p className="font-mono-data text-[10px] uppercase tracking-[0.14em] text-neutral-500 sm:text-[11px]">
              Sample class profile · preview
            </p>
          </div>
        </div>
        <span className="glass hidden rounded-full px-3 py-1.5 text-[11px] font-medium text-emerald-300 sm:inline-flex">
          <span className="mr-1.5 inline-block size-1.5 self-center rounded-full bg-emerald-400" /> live
        </span>
      </motion.div>

      {/* charts row: 2×2 on phone/tablet so the act fits the pinned viewport
          height, 4 across on desktop. overflow-hidden guards against any
          sub-pixel spill into the stat row below. */}
      <div className="mt-3 grid min-h-0 flex-1 grid-cols-2 gap-2.5 overflow-hidden sm:mt-4 sm:gap-3 lg:grid-cols-4">
        {/* gauge + percentile */}
        <motion.div style={gaugeR} className="glass flex min-w-0 flex-col items-center justify-center gap-3.5 rounded-2xl p-3.5 sm:p-4">
          <ScoreGauge p={p} />
          <div className="w-full max-w-[220px]">
            <motion.div style={pctR}>
              <Percentile p={p} />
            </motion.div>
          </div>
        </motion.div>

        {/* radar */}
        <motion.div style={radarR} className="glass flex min-w-0 flex-col rounded-2xl p-3.5 sm:p-4">
          <p className={["mb-1.5", SECTION_LABEL].join(" ")}>Per-topic mastery</p>
          <div className="mx-auto flex w-full max-w-[300px] flex-1 items-center">
            <Radar p={p} />
          </div>
        </motion.div>

        {/* trend */}
        <motion.div style={trendR} className="glass flex min-w-0 flex-col rounded-2xl p-3.5 sm:p-4">
          <div className="mb-1.5 flex items-center justify-between">
            <p className={SECTION_LABEL}>Test → retest</p>
            <span className="flex items-center gap-0.5 font-mono-data text-[11px] font-semibold text-emerald-300">
              <MaterialIcon name="trending" className="size-3.5" /> +29
            </span>
          </div>
          <div className="flex flex-1 items-center">
            <Trend p={p} />
          </div>
        </motion.div>

        {/* distribution */}
        <motion.div style={distR} className="glass flex min-w-0 flex-col rounded-2xl p-3.5 sm:p-4">
          <div className="mb-1.5 flex items-center justify-between">
            <p className={SECTION_LABEL}>Score distribution</p>
            <MaterialIcon name="stats" className="size-4 text-neutral-500" />
          </div>
          <div className="flex flex-1 items-center">
            <Distribution p={p} />
          </div>
        </motion.div>
      </div>

      {/* honest insight tiles — own non-overlapping row: 2-up phone, 4-up ≥sm */}
      <div className="mt-2.5 grid shrink-0 grid-cols-2 gap-2.5 sm:mt-3 sm:grid-cols-4">
        <StatTile p={p} from={0.9} to={0.99} value={15} label="Top score" suffix="/15" icon="trophy" accent="text-amber-300" />
        <StatTile p={p} from={0.9} to={0.99} value={28} label="Q12 hardest" suffix="%" icon="target" accent="text-rose-300" delay={0.01} />
        <StatTile p={p} from={0.9} to={0.99} value={4} label="To review" icon="task" accent="text-cyan-300" delay={0.02} />
        <StatTile p={p} from={0.9} to={0.99} value={110} label="Graded" icon="checklist" accent="text-emerald-300" delay={0.03} />
      </div>
    </div>
  )
}

// ── Static (reduced-motion) end-state of the dashboard ─────────────────────────
export function AnalyticsStatic() {
  return (
    <div className="glass-strong mx-auto w-full max-w-[1180px] rounded-[1.5rem] p-5 sm:p-6">
      <div className="flex items-center gap-2.5">
        <span className="flex size-9 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300">
          <MaterialIcon name="analytics" className="size-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-white">Class analytics</p>
          <p className="font-mono-data text-[10px] uppercase tracking-[0.14em] text-neutral-500">
            Sample class profile · preview
          </p>
        </div>
        <p className="ml-auto font-mono-data text-3xl font-semibold text-white">87%</p>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="glass rounded-xl p-3">
          <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.14em] text-neutral-400">Per-topic mastery</p>
          <div className="flex h-28 items-end gap-1.5">
            {RADAR.map((d, i) => (
              <div key={d.label} className="flex flex-1 flex-col items-center gap-1">
                <div className="flex h-full w-full items-end justify-center">
                  <div
                    className="w-3 rounded-t"
                    style={{ height: `${d.v * 100}%`, backgroundColor: ["#6366f1", "#38bdf8", "#2dd4bf", "#34d399", "#fbbf24", "#a78bfa"][i] }}
                  />
                </div>
                <span className="text-[8px] text-neutral-500">{d.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="glass rounded-xl p-3">
          <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.14em] text-neutral-400">Test → retest</p>
          <div className="flex h-28 items-end gap-1.5">
            {TREND.map((v, i) => (
              <div key={i} className="flex-1 rounded-t bg-emerald-400/70" style={{ height: `${((v - 50) / 45) * 100}%` }} />
            ))}
          </div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {[
          { v: "15/15", l: "Top score", icon: "trophy", a: "text-amber-300" },
          { v: "28%", l: "Q12 hardest", icon: "target", a: "text-rose-300" },
          { v: "4", l: "To review", icon: "task", a: "text-cyan-300" },
          { v: "110", l: "Graded", icon: "checklist", a: "text-emerald-300" },
        ].map((s) => (
          <div key={s.l} className="glass rounded-xl px-3 py-2.5">
            <div className="flex items-center gap-1.5 text-neutral-400">
              <MaterialIcon name={s.icon} className={["size-3.5", s.a].join(" ")} />
              <span className="text-[10px] font-medium uppercase tracking-[0.12em]">{s.l}</span>
            </div>
            <p className="mt-1 font-mono-data text-xl font-semibold text-white">{s.v}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
