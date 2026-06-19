/**
 * BubbleSheet — a stylized OMR answer sheet rendered as inline SVG.
 *
 * Flat + theme-aware: colors resolve from the app's semantic tokens
 * (--card / --foreground / --border / --muted-foreground) so the sheet flips
 * correctly with light/dark instead of owning a private dark palette. Marked
 * bubbles use the brand `tint` (defaults to --primary). Kept lightweight —
 * bubbles render statically (no per-sheet scroll observers).
 *
 * Props:
 *   name      student name shown in the header
 *   roll      digit string for the pre-bubbled roll grid (e.g. "101")
 *   answers   array (len = rows) of filled option index 0..3, or -1 for blank
 *   rows      number of answer rows to render (default 7; more ⇒ smaller bubbles)
 *   tint      CSS color for marked bubbles (defaults to the brand --primary)
 *   graded    show a "graded" score chip overlay
 *   score     e.g. "13/15"
 *   gradeKey  per-row correctness for the graded variant (true=correct)
 *   className wrapper classes
 */
const ROWS = 7
const OPTS = 4

// Theme-aware palette — resolves from app tokens so the sheet matches light/dark.
const SHEET = {
  paper: "var(--color-card)",
  paperEdge: "var(--color-border)",
  ink: "var(--color-foreground)",
  faint: "var(--color-muted-foreground)",
  line: "var(--color-border)",
  bubble: "var(--color-border-stronger)",
  fiducial: "var(--color-muted-foreground)",
}

// Deterministic seeded shuffle so each sheet looks visibly unique but stable.
function seededAnswers(seed, count = ROWS) {
  let s = (seed + 1) * 2654435761
  const out = []
  for (let i = 0; i < count; i++) {
    s = (s ^ (s << 13)) >>> 0
    s = (s ^ (s >> 17)) >>> 0
    s = (s ^ (s << 5)) >>> 0
    out.push(s % OPTS)
  }
  return out
}

export default function BubbleSheet({
  name = "Student",
  roll = "101",
  answers,
  seed = 0,
  rows = ROWS,
  tint = "var(--color-primary)",
  graded = false,
  score = "13/15",
  gradeKey,
  className = "",
}) {
  const marks = answers ?? seededAnswers(seed, rows)
  const rollDigits = String(roll).padStart(3, "0").slice(0, 3).split("").map(Number)
  // Default correctness pattern for the graded chip checkmarks.
  const key = gradeKey ?? marks.map((_, i) => (i + seed) % 4 !== 0)

  // Adaptive answer-row geometry: more rows ⇒ tighter pitch + smaller bubbles so a
  // denser sheet (e.g. rows=14) still fits the 200×264 viewBox. At the default 7
  // rows this reproduces the original pitch (16) and bubble radii (5.6 / 4.7).
  const rowTop = 72
  const rowPitch = Math.min(16, (210 - rowTop) / Math.max(rows - 1, 1))
  const rOuter = Math.min(5.6, rowPitch * 0.36)
  const rFill = rOuter * 0.84
  const bubbleStroke = rOuter > 4.6 ? 1.1 : 0.9
  const rowLabelSize = Math.min(6, rowPitch * 0.4)

  return (
    <div className={className}>
      <svg
        viewBox="0 0 200 264"
        className="h-full w-full"
        role="img"
        aria-label={`OMR answer sheet for ${name}`}
      >
        {/* paper */}
        <rect x="3" y="3" width="194" height="258" rx="11" fill={SHEET.paper}
          stroke={SHEET.paperEdge} strokeWidth="1.5" />

        {/* corner fiducials */}
        {[[14, 14], [14, 240], [178, 240]].map(([x, y], i) => (
          <rect key={i} x={x} y={y} width="8" height="8" rx="1.5" fill={SHEET.fiducial} />
        ))}

        {/* QR block (stylized) top-right — 5×5 module grid for clarity */}
        <g>
          <rect x="146" y="10" width="36" height="36" rx="2.5" fill={SHEET.ink} opacity="0.10" />
          {Array.from({ length: 25 }).map((_, i) => {
            const r = Math.floor(i / 5)
            const c = i % 5
            const on = (r * 7 + c * 5 + (r === c ? 3 : 0) + seed) % 3 === 0
            return on ? (
              <rect key={i} x={149 + c * 6.4} y={13 + r * 6.4} width="5" height="5" rx="0.6" fill={SHEET.ink} />
            ) : null
          })}
        </g>

        {/* header */}
        <text x="16" y="34" fontSize="7" fontWeight="700" letterSpacing="0.5"
          fill={SHEET.ink} fontFamily="ui-sans-serif, system-ui">
          ANSWER SHEET
        </text>
        <text x="16" y="44" fontSize="6.5" fill={SHEET.faint}
          fontFamily="ui-sans-serif, system-ui">
          {name}
        </text>
        <line x1="14" y1="50" x2="186" y2="50" stroke={SHEET.line} strokeWidth="1" />

        {/* roll grid */}
        <text x="16" y="62" fontSize="5.5" fontWeight="600" fill={SHEET.faint}
          fontFamily="ui-sans-serif, system-ui">
          ROLL
        </text>
        {rollDigits.map((digit, col) =>
          Array.from({ length: 10 }).map((_, row) => {
            const cx = 20 + col * 11
            const cy = 70 + row * 11
            const filled = row === digit
            return (
              <circle
                key={`${col}-${row}`}
                cx={cx}
                cy={cy}
                r="2.7"
                fill={filled ? tint : "none"}
                stroke={filled ? tint : SHEET.bubble}
                strokeWidth="0.8"
              />
            )
          })
        )}

        {/* answer rows (static — lightweight for many fan instances) */}
        {marks.slice(0, rows).map((marked, row) => {
          const y = rowTop + row * rowPitch
          return (
            <g key={row}>
              <text x="64" y={y + 2} fontSize={rowLabelSize} fill={SHEET.faint}
                fontFamily="ui-sans-serif, system-ui" textAnchor="end">
                {row + 1}
              </text>
              {Array.from({ length: OPTS }).map((_, opt) => {
                const cx = 80 + opt * 21
                const isMarked = opt === marked
                return (
                  <g key={opt}>
                    <circle cx={cx} cy={y} r={rOuter} fill="none"
                      stroke={SHEET.bubble} strokeWidth={bubbleStroke} />
                    {isMarked && <circle cx={cx} cy={y} r={rFill} fill={tint} />}
                  </g>
                )
              })}
              {/* graded tick / cross per row */}
              {graded && (
                key[row] ? (
                  <path
                    d={`M168 ${y - 1.5} l2.4 2.6 l4.4 -5`}
                    stroke="var(--color-success)" strokeWidth="1.7" fill="none"
                    strokeLinecap="round" strokeLinejoin="round"
                  />
                ) : (
                  <path
                    d={`M168 ${y - 3} l5 5 m0 -5 l-5 5`}
                    stroke="var(--color-destructive)" strokeWidth="1.6" fill="none" strokeLinecap="round"
                  />
                )
              )}
            </g>
          )
        })}

        {/* footer barcode */}
        <g opacity="0.5">
          {Array.from({ length: 26 }).map((_, i) => (
            <rect key={i} x={16 + i * 2.4} y="225" width={(i + seed) % 3 === 0 ? 1.6 : 0.8} height="9"
              fill={SHEET.ink} />
          ))}
        </g>

        {/* graded score chip */}
        {graded && (
          <g>
            <rect x="112" y="90" width="74" height="34" rx="8" fill="var(--color-surface-2)"
              stroke={tint} strokeWidth="1.5" />
            <circle cx="127" cy="107" r="7" fill="var(--color-success)" />
            <path d="M123.5 107 L126 109.5 L130.5 104.5" stroke="var(--color-card)" strokeWidth="1.7"
              fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <text x="139" y="110" fontSize="10" fontWeight="700" fill={SHEET.ink}
              fontFamily="ui-sans-serif, system-ui">
              {score}
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}

// ── ShuffledSheet — a BubbleSheet with a per-seed unique answer order + name ──
export function ShuffledSheet({ seed = 0, name, roll, tint, rows, className = "" }) {
  return (
    <BubbleSheet
      seed={seed}
      name={name}
      roll={roll}
      tint={tint}
      rows={rows}
      className={className}
    />
  )
}

// ── GradedSheet — a BubbleSheet with the graded overlay ──
export function GradedSheet({ seed = 0, name, roll, tint, score = "13/15", rows, className = "" }) {
  return (
    <BubbleSheet
      seed={seed}
      name={name}
      roll={roll}
      tint={tint}
      graded
      score={score}
      rows={rows}
      className={className}
    />
  )
}
