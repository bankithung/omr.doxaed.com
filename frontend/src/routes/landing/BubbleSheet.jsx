/**
 * BubbleSheet — a stylized OMR answer sheet rendered as inline SVG.
 *
 * On the cinematic landing this renders in DARK mode with EXPLICIT colors
 * (the landing owns a self-contained dark canvas; it must not depend on the
 * app's light theme tokens). Kept lightweight: many instances render in the
 * Act 2 fan-out, so by default bubbles render statically (no per-sheet
 * scroll observers). Pass `animateIn` for the legacy stagger-in behaviour.
 *
 * Props:
 *   name      student name shown in the header
 *   roll      digit string for the pre-bubbled roll grid (e.g. "101")
 *   answers   array (len = ROWS) of filled option index 0..3, or -1 for blank
 *   tint      CSS color for marked bubbles
 *   graded    show a "graded" score chip overlay
 *   score     e.g. "13/15"
 *   gradeKey  per-row correctness for the graded variant (true=correct)
 *   gradeReveal  0..1 — fraction of graded marks revealed (for scrub wipe)
 *   className wrapper classes
 */
const ROWS = 7
const OPTS = 4

// Self-contained dark palette (do NOT reference app theme tokens here).
const DARK = {
  paper: "#0f1120",
  paperEdge: "rgba(255,255,255,0.12)",
  ink: "#eef0fb",
  faint: "rgba(238,240,251,0.55)",
  line: "rgba(255,255,255,0.14)",
  bubble: "rgba(255,255,255,0.22)",
  fiducial: "#eef0fb",
}

// Deterministic seeded shuffle so each sheet looks visibly unique but stable.
function seededAnswers(seed) {
  let s = (seed + 1) * 2654435761
  const out = []
  for (let i = 0; i < ROWS; i++) {
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
  tint = "#6366f1",
  graded = false,
  score = "13/15",
  gradeKey,
  className = "",
}) {
  const marks = answers ?? seededAnswers(seed)
  const rollDigits = String(roll).padStart(3, "0").slice(0, 3).split("").map(Number)
  // Default correctness pattern for the graded chip checkmarks.
  const key = gradeKey ?? marks.map((_, i) => (i + seed) % 4 !== 0)

  return (
    <div className={className}>
      <svg
        viewBox="0 0 200 264"
        className="h-full w-full"
        role="img"
        aria-label={`OMR answer sheet for ${name}`}
      >
        {/* paper */}
        <rect x="3" y="3" width="194" height="258" rx="11" fill={DARK.paper}
          stroke={DARK.paperEdge} strokeWidth="1.5" />

        {/* corner fiducials */}
        {[[14, 14], [14, 240], [178, 240]].map(([x, y], i) => (
          <rect key={i} x={x} y={y} width="8" height="8" rx="1.5" fill={DARK.fiducial} />
        ))}

        {/* QR block (stylized) top-right — 5×5 module grid for clarity */}
        <g>
          <rect x="146" y="10" width="36" height="36" rx="2.5" fill={DARK.ink} opacity="0.10" />
          {Array.from({ length: 25 }).map((_, i) => {
            const r = Math.floor(i / 5)
            const c = i % 5
            const on = (r * 7 + c * 5 + (r === c ? 3 : 0) + seed) % 3 === 0
            return on ? (
              <rect key={i} x={149 + c * 6.4} y={13 + r * 6.4} width="5" height="5" rx="0.6" fill={DARK.ink} />
            ) : null
          })}
        </g>

        {/* header */}
        <text x="16" y="34" fontSize="7" fontWeight="700" letterSpacing="0.5"
          fill={DARK.ink} fontFamily="ui-sans-serif, system-ui">
          ANSWER SHEET
        </text>
        <text x="16" y="44" fontSize="6.5" fill={DARK.faint}
          fontFamily="ui-sans-serif, system-ui">
          {name}
        </text>
        <line x1="14" y1="50" x2="186" y2="50" stroke={DARK.line} strokeWidth="1" />

        {/* roll grid */}
        <text x="16" y="62" fontSize="5.5" fontWeight="600" fill={DARK.faint}
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
                stroke={filled ? tint : DARK.bubble}
                strokeWidth="0.8"
              />
            )
          })
        )}

        {/* answer rows (static — lightweight for many fan instances) */}
        {marks.slice(0, ROWS).map((marked, row) => {
          const y = 72 + row * 16
          return (
            <g key={row}>
              <text x="64" y={y + 2} fontSize="6" fill={DARK.faint}
                fontFamily="ui-sans-serif, system-ui" textAnchor="end">
                {row + 1}
              </text>
              {Array.from({ length: OPTS }).map((_, opt) => {
                const cx = 80 + opt * 21
                const isMarked = opt === marked
                return (
                  <g key={opt}>
                    <circle cx={cx} cy={y} r="5.6" fill="none"
                      stroke={DARK.bubble} strokeWidth="1.1" />
                    {isMarked && <circle cx={cx} cy={y} r="4.7" fill={tint} />}
                  </g>
                )
              })}
              {/* graded tick / cross per row */}
              {graded && (
                key[row] ? (
                  <path
                    d={`M168 ${y - 1.5} l2.4 2.6 l4.4 -5`}
                    stroke="#34d399" strokeWidth="1.7" fill="none"
                    strokeLinecap="round" strokeLinejoin="round"
                  />
                ) : (
                  <path
                    d={`M168 ${y - 3} l5 5 m0 -5 l-5 5`}
                    stroke="#fb7185" strokeWidth="1.6" fill="none" strokeLinecap="round"
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
              fill={DARK.ink} />
          ))}
        </g>

        {/* graded score chip */}
        {graded && (
          <g>
            <rect x="112" y="90" width="74" height="34" rx="8" fill="#11131f"
              stroke={tint} strokeWidth="1.5" />
            <circle cx="127" cy="107" r="7" fill="#34d399" />
            <path d="M123.5 107 L126 109.5 L130.5 104.5" stroke="#0f1120" strokeWidth="1.7"
              fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <text x="139" y="110" fontSize="10" fontWeight="700" fill={DARK.ink}
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
export function ShuffledSheet({ seed = 0, name, roll, tint, className = "" }) {
  return (
    <BubbleSheet
      seed={seed}
      name={name}
      roll={roll}
      tint={tint}
      className={className}
    />
  )
}

// ── GradedSheet — a BubbleSheet with the graded overlay ──
export function GradedSheet({ seed = 0, name, roll, tint, score = "13/15", className = "" }) {
  return (
    <BubbleSheet
      seed={seed}
      name={name}
      roll={roll}
      tint={tint}
      graded
      score={score}
      className={className}
    />
  )
}
