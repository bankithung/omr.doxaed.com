import BubbleSheet, { ShuffledSheet, GradedSheet } from "./BubbleSheet"
import MaterialIcon from "./MaterialIcon"
import { InViewAnim } from "./motion/reveal"

/**
 * ProductGraphics — the flat, premium, ANIMATED product visuals that give the
 * landing its Supabase "images that animate" feel. Every graphic is built from
 * the app's semantic tokens (theme-aware, flat — no colored gradients) and runs
 * its motion only on scroll-in via `<InViewAnim>` (which arms the CSS keyframes
 * in index.css). All animations collapse to their finished frame under
 * prefers-reduced-motion, so each graphic reads as a clean static screenshot
 * for reduced-motion users.
 *
 * Exports:
 *   DashboardPreview — the large hero "app screenshot" composition.
 *   AnalyticsChart   — bars + a drawn trend line that grow on reveal.
 *   ScanSheet        — an answer sheet with a scan-line sweep + read chips.
 *   DealOut          — one bank + one roster → many shuffled sheets (fan-out).
 */

// ── Small primitives ──────────────────────────────────────────────────────────

function WindowChrome({ label, children, className = "" }) {
  return (
    <div className={`overflow-hidden rounded-xl border border-border bg-card ${className}`}>
      <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-3 py-2">
        <span className="flex gap-1.5" aria-hidden>
          <span className="size-2.5 rounded-full bg-border-stronger" />
          <span className="size-2.5 rounded-full bg-border-stronger" />
          <span className="size-2.5 rounded-full bg-border-stronger" />
        </span>
        <span className="ml-1 truncate font-mono text-[11px] text-muted-foreground">{label}</span>
        <span className="ml-auto flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span className="landing-pulse size-1.5 rounded-full bg-primary" />
          <span className="font-mono uppercase tracking-[0.12em]">live</span>
        </span>
      </div>
      {children}
    </div>
  )
}

function StatTile({ label, value, sub }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-medium tabular text-foreground">{value}</p>
      {sub ? <p className="text-[11px] text-muted-foreground">{sub}</p> : null}
    </div>
  )
}

// Per-topic mastery — a labelled mini bar row that grows on reveal.
const TOPICS = [
  ["Kinematics", 86],
  ["Optics", 71],
  ["Thermo", 64],
  ["Circuits", 52],
]
function TopicMastery() {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="mb-3 text-sm font-medium text-foreground">Per-topic mastery</p>
      <ul className="space-y-2.5">
        {TOPICS.map(([name, pct], i) => (
          <li key={name} className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-2.5">
            <span className="truncate text-[11px] text-muted-foreground">{name}</span>
            <span className="h-1.5 overflow-hidden rounded-full bg-surface-2">
              <span
                className="landing-bar-x block h-full rounded-full bg-primary"
                style={{ width: `${pct}%`, animationDelay: `${i * 80}ms` }}
              />
            </span>
            <span className="text-right font-mono text-[11px] tabular text-muted-foreground">{pct}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Compact reliability / median / hardest-question stat strip.
function MetricStrip() {
  const items = [
    ["Reliability (KR-20)", "0.82"],
    ["Median", "74%"],
    ["Hardest", "Q12 · 28%"],
  ]
  return (
    <div className="grid grid-cols-3 divide-x divide-border overflow-hidden rounded-xl border border-border bg-surface-2">
      {items.map(([label, value]) => (
        <div key={label} className="px-3 py-2.5">
          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted-foreground">{label}</p>
          <p className="mt-0.5 text-sm font-medium tabular text-foreground">{value}</p>
        </div>
      ))}
    </div>
  )
}

// ── AnalyticsChart — flat bars + a drawn trend line that grow on reveal ────────

const BARS = [34, 52, 41, 68, 59, 82, 74, 96]

export function AnalyticsChart({ className = "", label = "Score distribution" }) {
  // Build the trend polyline across the tops of the bars.
  const w = 280
  const h = 120
  const step = w / (BARS.length - 1)
  const pts = BARS.map((v, i) => [i * step, h - (v / 100) * h])
  const linePath = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ")

  return (
    <InViewAnim className={className}>
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">{label}</p>
          <span className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
            <MaterialIcon name="trending" className="size-3.5 text-primary" />
            +12% vs last test
          </span>
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} className="h-32 w-full" role="img" aria-label="Score distribution chart">
          {/* baseline */}
          <line x1="0" y1={h - 0.5} x2={w} y2={h - 0.5} stroke="var(--color-border)" strokeWidth="1" />
          {/* bars */}
          {BARS.map((v, i) => {
            const bw = step * 0.5
            const bh = (v / 100) * h
            return (
              <rect
                key={i}
                className="landing-bar"
                x={i * step - bw / 2 + (i === 0 ? bw / 2 : 0)}
                y={h - bh}
                width={bw}
                height={bh}
                rx="2"
                fill="var(--color-primary)"
                opacity="0.22"
                style={{ animationDelay: `${i * 60}ms` }}
              />
            )
          })}
          {/* drawn trend line */}
          <path
            className="landing-draw"
            d={linePath}
            fill="none"
            stroke="var(--color-primary)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ "--draw-len": 360 }}
          />
          {pts.map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r="2.4" fill="var(--color-primary)" className="landing-bar" style={{ animationDelay: `${500 + i * 40}ms` }} />
          ))}
        </svg>
      </div>
    </InViewAnim>
  )
}

// ── ScanSheet — an answer sheet with a scan-line sweep + read chips ────────────

export function ScanSheet({ className = "" }) {
  return (
    <InViewAnim className={className}>
      <div className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
        <div className="relative mx-auto max-w-[220px]">
          <BubbleSheet seed={4} name="Rahul K." roll="102" className="aspect-[200/264]" />
          {/* scan-line sweep — thin band travels top→bottom; hidden under reduced motion */}
          <div
            aria-hidden
            className="landing-scanline pointer-events-none absolute inset-x-2 top-2 h-6 rounded-sm"
            style={{
              "--scan-travel": "230px",
              background:
                "linear-gradient(to bottom, transparent, color-mix(in oklch, var(--color-primary) 30%, transparent), transparent)",
              boxShadow: "0 0 0 1px color-mix(in oklch, var(--color-primary) 35%, transparent)",
            }}
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-muted-foreground">
            <MaterialIcon name="task" className="size-3 text-success" /> 47 read
          </span>
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-muted-foreground">
            <MaterialIcon name="shield" className="size-3 text-primary" /> 2 to review
          </span>
          <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-muted-foreground">
            <MaterialIcon name="bolt" className="size-3 text-primary" /> aligned by QR
          </span>
        </div>
      </div>
    </InViewAnim>
  )
}

// ── DealOut — one bank + one roster → many shuffled sheets (fan-out) ───────────

export function DealOut({ className = "" }) {
  const fan = [
    { seed: 3, name: "Asha D.", roll: "101", x: "-22px", delay: 80 },
    { seed: 5, name: "Rahul K.", roll: "102", x: "0px", delay: 200 },
    { seed: 9, name: "Meera S.", roll: "103", x: "22px", delay: 320 },
  ]
  return (
    <InViewAnim className={className}>
      <div className="grid items-center gap-5 rounded-xl border border-border bg-card p-5 sm:grid-cols-[auto_1fr]">
        {/* source: one bank + one roster */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2.5 rounded-lg border border-border bg-surface-2 px-3 py-2.5">
            <span className="flex size-8 items-center justify-center rounded-md border border-border bg-card text-primary">
              <MaterialIcon name="checklist" className="size-4" />
            </span>
            <div>
              <p className="text-xs font-medium text-foreground">One question bank</p>
              <p className="font-mono text-[10px] text-muted-foreground">25 MCQs</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-lg border border-border bg-surface-2 px-3 py-2.5">
            <span className="flex size-8 items-center justify-center rounded-md border border-border bg-card text-primary">
              <MaterialIcon name="groups" className="size-4" />
            </span>
            <div>
              <p className="text-xs font-medium text-foreground">One roster</p>
              <p className="font-mono text-[10px] text-muted-foreground">Class X · 40 students</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 self-center font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            shuffle
            <MaterialIcon name="arrow" className="size-3.5 text-primary" />
          </div>
        </div>

        {/* dealt-out shuffled sheets */}
        <div className="flex items-end justify-center gap-2 sm:justify-end">
          {fan.map((f) => (
            <div
              key={f.seed}
              className="landing-deal w-[28%] max-w-[110px] rounded-lg border border-border bg-surface-2 p-1.5"
              style={{ "--deal-from-x": f.x, "--deal-delay": `${f.delay}ms` }}
            >
              <ShuffledSheet seed={f.seed} name={f.name} roll={f.roll} className="aspect-[200/264]" />
            </div>
          ))}
        </div>
      </div>
    </InViewAnim>
  )
}

// ── DashboardPreview — the large hero "app screenshot" composition ─────────────

export function DashboardPreview({ className = "" }) {
  return (
    <WindowChrome label="omr.doxaed.com/tests/midterm-physics" className={`shadow-xl ${className}`}>
      <InViewAnim className="grid gap-3 p-3 sm:p-4 lg:grid-cols-[1.35fr_1fr]">
        {/* left: header + stats + chart */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Midterm · Physics</p>
              <p className="font-mono text-[11px] text-muted-foreground">49 sheets · graded · public results on</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-foreground">
              <MaterialIcon name="task" className="size-3.5 text-success" /> Graded
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2.5">
            <StatTile label="Mean" value="72%" sub="+4 pts" />
            <StatTile label="Top score" value="96%" sub="Asha D." />
            <StatTile label="To review" value="2" sub="low-confidence" />
          </div>

          <AnalyticsChart label="Score distribution" />

          {/* keep the left column as tall + complete as the sheet on the right */}
          <MetricStrip />
          <TopicMastery />
        </div>

        {/* right: a real graded sheet + roster rows */}
        <div className="flex flex-col gap-3">
          <div className="rounded-xl border border-border bg-surface-2 p-2.5">
            <GradedSheet seed={7} name="Asha D." roll="101" score="14/15" className="aspect-[200/264]" />
          </div>
          <div className="rounded-xl border border-border bg-surface-2 p-3">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Top results</p>
            <ul className="space-y-1.5">
              {[
                ["Asha D.", "14/15"],
                ["Rahul K.", "13/15"],
                ["Meera S.", "13/15"],
              ].map(([n, s]) => (
                <li key={n} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-2 text-foreground">
                    <span className="flex size-5 items-center justify-center rounded-full border border-border bg-card font-mono text-[10px] text-muted-foreground">
                      {n[0]}
                    </span>
                    {n}
                  </span>
                  <span className="font-mono tabular text-muted-foreground">{s}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </InViewAnim>
    </WindowChrome>
  )
}
