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
            <MaterialIcon name="trending" className="size-3.5 text-indigo" />
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

// Shared footer stats — "47 read · 2 to review · aligned by QR".
function ScanStats() {
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-muted-foreground">
        <MaterialIcon name="task" className="size-3 text-success" /> 47 read
      </span>
      <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-muted-foreground">
        <MaterialIcon name="shield" className="size-3 text-[var(--color-warning)]" /> 2 to review
      </span>
      <span className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-[11px] text-muted-foreground">
        <MaterialIcon name="bolt" className="size-3 text-indigo" /> aligned by QR
      </span>
    </div>
  )
}

// 20 deterministic answers (filled option A–D index 0..3) for the full sheet.
const FULL_ANSWERS = [
  3, 0, 2, 1, 0, 3, 1, 2, 0, 3, // Q1, Q10
  1, 2, 3, 0, 2, 1, 3, 0, 2, 1, // Q11, Q20
]
const REVIEW_ROWS = new Set([5, 14]) // 0-based → Q6 & Q15 get a double-mark flag
const FAINT_ROWS = new Set([9]) // Q10 reads faint / low-confidence
const OPT_LABELS = ["A", "B", "C", "D"]

// One question row: index + 4 labelled bubbles, exactly one filled (green).
// Review rows carry an amber ring + a faint 2nd mark; faint rows read lighter.
function FullRow({ q, marked, review, faint, delay }) {
  return (
    <div
      className={[
        "landing-deal flex items-center gap-1.5 rounded-md px-1.5 py-1",
        review
          ? "bg-[color-mix(in_oklch,var(--color-warning)_8%,transparent)] ring-1 ring-[var(--color-warning)]/60"
          : "",
      ].join(" ")}
      style={{ "--deal-delay": `${delay}ms`, "--deal-from-x": "0px" }}
    >
      <span className="w-4 shrink-0 text-right font-mono text-[9px] tabular text-muted-foreground">{q}</span>
      <div className="flex items-center gap-1">
        {OPT_LABELS.map((label, opt) => {
          const isMarked = opt === marked
          const isGhost = review && opt === (marked + 2) % 4 // ambiguous 2nd mark
          return (
            <span
              key={label}
              className={[
                "flex size-[13px] items-center justify-center rounded-full border text-[7px] font-medium leading-none",
                isMarked
                  ? faint
                    ? "border-indigo/50 bg-indigo/40 text-primary-foreground/80"
                    : "border-indigo bg-primary text-primary-foreground"
                  : isGhost
                    ? "border-[var(--color-warning)] bg-[color-mix(in_oklch,var(--color-warning)_45%,transparent)] text-foreground"
                    : "border-border-stronger text-transparent",
              ].join(" ")}
            >
              {label}
            </span>
          )
        })}
      </div>
    </div>
  )
}

/**
 * FullAnswerSheet — an opt-in (variant="full") denser OMR card: a real-looking
 * 20-question sheet laid out as TWO columns of 10 (Q1–Q10 / Q11–Q20), with a
 * header (ANSWER SHEET eyebrow, student + roll, a QR-alignment glyph), exactly
 * one green-filled bubble per row, two amber review-flagged rows and one faint
 * row (matching the "2 to review" stat). Taller + denser than the default sheet
 * so it balances a tall copy column. The two columns always stay side by side
 * and shrink gracefully on narrow widths (no horizontal overflow).
 */
function FullAnswerSheet() {
  const left = FULL_ANSWERS.slice(0, 10)
  const right = FULL_ANSWERS.slice(10, 20)
  return (
    <div className="rounded-lg border border-border bg-surface-1 p-3 sm:p-4">
      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Answer sheet
          </p>
          <p className="mt-1 truncate text-sm font-medium text-foreground">Rahul K.</p>
          <p className="font-mono text-[10px] text-muted-foreground">
            ROLL <span className="text-foreground">102</span>
          </p>
        </div>
        {/* QR-alignment glyph (5×5) — matches the "aligned by QR" footer pill */}
        <div aria-hidden className="grid shrink-0 grid-cols-5 gap-px rounded-sm border border-border bg-card p-1">
          {Array.from({ length: 25 }).map((_, i) => {
            const r = Math.floor(i / 5)
            const c = i % 5
            const on = (r * 7 + c * 5 + (r === c ? 3 : 0)) % 3 === 0
            return <span key={i} className={["size-1 rounded-[1px]", on ? "bg-foreground" : "bg-transparent"].join(" ")} />
          })}
        </div>
      </div>

      <div className="my-2.5 h-px bg-border" />

      {/* two columns of 10 rows */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        <div className="space-y-0.5">
          {left.map((marked, i) => (
            <FullRow
              key={i}
              q={i + 1}
              marked={marked}
              review={REVIEW_ROWS.has(i)}
              faint={FAINT_ROWS.has(i)}
              delay={i * 35}
            />
          ))}
        </div>
        <div className="space-y-0.5">
          {right.map((marked, i) => (
            <FullRow
              key={i}
              q={i + 11}
              marked={marked}
              review={REVIEW_ROWS.has(i + 10)}
              faint={FAINT_ROWS.has(i + 10)}
              delay={(i + 10) * 35}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * ScanSheet — the default is the compact single SVG sheet with a scan-line sweep
 * (used by Hero/DashboardPreview/HowItWorks — UNCHANGED). Pass `variant="full"`
 * for the denser two-column 20-question OMR card (used by TrustSection to
 * balance its tall copy column). Both share the read/review/QR stat footer and
 * stay reduced-motion-safe via `InViewAnim` + the landing keyframes.
 */
export function ScanSheet({ className = "", variant = "default" }) {
  if (variant === "full") {
    return (
      <InViewAnim className={className}>
        <div className="relative overflow-hidden rounded-xl border border-border bg-card p-4">
          <div className="relative mx-auto max-w-[440px]">
            <FullAnswerSheet />
            {/* scan-line sweep — travels across the taller card; hidden under reduced motion */}
            <div
              aria-hidden
              className="landing-scanline pointer-events-none absolute inset-x-2 top-2 h-7 rounded-sm"
              style={{
                "--scan-travel": "380px",
                background:
                  "linear-gradient(to bottom, transparent, color-mix(in oklch, var(--color-primary) 26%, transparent), transparent)",
                boxShadow: "0 0 0 1px color-mix(in oklch, var(--color-primary) 32%, transparent)",
              }}
            />
          </div>
          <ScanStats />
        </div>
      </InViewAnim>
    )
  }

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
        <ScanStats />
      </div>
    </InViewAnim>
  )
}

// ── DealOut — one bank + one roster → many shuffled sheets (fan-out) ───────────

// Animated connector — amber flow lines bridging the bank+roster (left) to the
// dealt sheets (right), filling what used to be a large empty gap. Marching
// dashes (landing-flow) over faint static rails read as sheets streaming out.
// Used in the wide/row layout; the stacked (mobile) layout uses the vertical
// variant below. Reduced-motion: the dashes hold still (rails stay for structure).
function DealConnector() {
  const paths = [
    "M2 78 C 48 78, 66 30, 120 30",
    "M2 78 C 54 78, 74 78, 120 78",
    "M2 78 C 48 78, 66 126, 120 126",
  ]
  return (
    <svg
      viewBox="0 0 120 156"
      preserveAspectRatio="none"
      aria-hidden
      className="h-[140px] w-full"
    >
      {/* faint static amber rails — structure survives without motion */}
      {paths.map((d, i) => (
        <path
          key={`rail-${i}`}
          d={d}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="1.25"
          strokeOpacity="0.28"
          vectorEffect="non-scaling-stroke"
        />
      ))}
      {/* marching amber flow */}
      {paths.map((d, i) => (
        <path
          key={`flow-${i}`}
          className="landing-flow"
          d={d}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="2.25"
          strokeOpacity="0.95"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
          style={{ animationDelay: `${i * 160}ms` }}
        />
      ))}
      {/* endpoint nodes where each flow lands (one per dealt sheet) */}
      {[30, 78, 126].map((cy, i) => (
        <circle key={`end-${i}`} cx="119" cy={cy} r="2.4" fill="var(--color-primary)" vectorEffect="non-scaling-stroke" />
      ))}
    </svg>
  )
}

// Vertical variant for the stacked (mobile) layout — the flow runs top→down from
// the source to the sheets, so the marching dashes + chevron face DOWN (a
// right-facing arrow makes no sense once the layout stacks).
function DealConnectorVertical() {
  return (
    <svg viewBox="0 0 24 46" aria-hidden="true" className="h-11 w-6">
      <line x1="12" y1="3" x2="12" y2="32" stroke="var(--color-primary)" strokeWidth="1.25" strokeOpacity="0.28" />
      <line
        x1="12"
        y1="3"
        x2="12"
        y2="32"
        className="landing-flow"
        stroke="var(--color-primary)"
        strokeWidth="2.25"
        strokeOpacity="0.95"
        strokeLinecap="round"
      />
      <path
        d="M6 30 L12 39 L18 30"
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function DealOut({ className = "" }) {
  const fan = [
    { seed: 3, name: "Asha D.", roll: "101", x: "-22px", delay: 80 },
    { seed: 5, name: "Rahul K.", roll: "102", x: "0px", delay: 200 },
    { seed: 9, name: "Meera S.", roll: "103", x: "22px", delay: 320 },
  ]
  return (
    <InViewAnim className={`@container ${className}`}>
      <div className="flex flex-col items-center gap-6 overflow-hidden rounded-xl border border-border bg-card p-5 @lg:flex-row @lg:justify-center">
        {/* source: one bank + one roster */}
        <div className="flex w-full flex-col gap-3 @lg:w-auto @lg:flex-none">
          <div className="flex items-center gap-2.5 rounded-lg border border-border bg-surface-2 px-3 py-2.5">
            <span className="flex size-8 items-center justify-center rounded-md border border-border bg-card text-indigo">
              <MaterialIcon name="checklist" className="size-4" />
            </span>
            <div>
              <p className="text-xs font-medium text-foreground">One question bank</p>
              <p className="font-mono text-[10px] text-muted-foreground">25 MCQs</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-lg border border-border bg-surface-2 px-3 py-2.5">
            <span className="flex size-8 items-center justify-center rounded-md border border-border bg-card text-indigo">
              <MaterialIcon name="groups" className="size-4" />
            </span>
            <div>
              <p className="text-xs font-medium text-foreground">One roster</p>
              <p className="font-mono text-[10px] text-muted-foreground">Class X · 40 students</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 self-center font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            shuffle
            <MaterialIcon name="arrow" className="size-3.5 rotate-90 text-indigo @lg:rotate-0" />
          </div>
        </div>

        {/* connector — a vertical down-flow when stacked (mobile: the source flows
            DOWN to the sheets), or the horizontal fan when the container is wide
            enough for a row (desktop). Width-capped so it never goes sparse. */}
        <div className="flex justify-center @lg:hidden">
          <DealConnectorVertical />
        </div>
        <div className="hidden max-w-[130px] flex-1 self-center @lg:block @3xl:max-w-[210px]">
          <DealConnector />
        </div>

        {/* dealt-out shuffled sheets — sized to the CONTAINER (compact in the Bento
            tile, prominent in the full-width HowItWorks card) */}
        <div className="flex w-full items-end justify-center gap-2 @lg:w-auto @lg:flex-none">
          {fan.map((f) => (
            <div
              key={f.seed}
              className="landing-deal min-w-0 max-w-[116px] flex-1 rounded-lg border border-border bg-surface-2 p-1.5 @lg:w-[64px] @lg:max-w-none @lg:flex-none @2xl:w-[80px] @4xl:w-[96px] @5xl:w-[108px]"
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
            <GradedSheet seed={7} name="Asha D." roll="101" score="14/15" rows={14} className="aspect-[200/264]" />
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
