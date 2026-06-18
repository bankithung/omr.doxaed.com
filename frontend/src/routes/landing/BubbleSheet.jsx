import { useRef } from "react"
import { motion, useInView, useReducedMotion } from "framer-motion"

/**
 * BubbleSheet — a stylized, animated OMR answer sheet rendered as inline SVG.
 * Uses flat theme tokens only. Bubbles fill in (staggered) when the
 * sheet scrolls into view; optional scan-line sweep and "graded" overlay.
 *
 * Props:
 *   name      student name shown in the header
 *   roll      digit string for the pre-bubbled roll grid (e.g. "101")
 *   answers   array (len = ROWS) of filled option index 0..3, or -1 for blank
 *   tint      CSS color for the marked bubbles (defaults to brand primary)
 *   scanning  show a sweeping scan line
 *   graded    show a "graded" score overlay
 *   score     e.g. "13/15"
 *   className wrapper classes
 */
const ROWS = 7
const OPTS = 4

export default function BubbleSheet({
  name = "Student",
  roll = "101",
  answers = [1, 2, 0, 3, 1, 0, 2],
  tint = "var(--primary)",
  scanning = false,
  graded = false,
  score = "13/15",
  className = "",
}) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: "-40px" })
  const reduce = useReducedMotion()
  const animate = inView && !reduce

  // Roll grid: 3 columns × 10 rows of small dots; fill the row matching each digit.
  const rollDigits = String(roll).padStart(3, "0").slice(0, 3).split("").map(Number)

  return (
    <div ref={ref} className={className}>
      <svg
        viewBox="0 0 200 264"
        className="h-full w-full"
        role="img"
        aria-label={`OMR answer sheet for ${name}`}
      >
        {/* paper */}
        <rect x="3" y="3" width="194" height="258" rx="11" fill="var(--card)"
          stroke="var(--border)" strokeWidth="1.5" />

        {/* corner fiducials */}
        {[[14, 14], [14, 240], [178, 240]].map(([x, y], i) => (
          <rect key={i} x={x} y={y} width="8" height="8" rx="1.5" fill="var(--foreground)" />
        ))}

        {/* QR block (stylized) top-right */}
        <g>
          <rect x="150" y="12" width="32" height="32" rx="2" fill="var(--foreground)" opacity="0.08" />
          {Array.from({ length: 16 }).map((_, i) => {
            const r = Math.floor(i / 4)
            const c = i % 4
            const on = (r * 7 + c * 5 + (r === c ? 3 : 0)) % 3 === 0
            return on ? (
              <rect key={i} x={153 + c * 7} y={15 + r * 7} width="5" height="5" fill="var(--foreground)" />
            ) : null
          })}
        </g>

        {/* header */}
        <text x="16" y="34" fontSize="7" fontWeight="700" letterSpacing="0.5"
          fill="var(--foreground)" fontFamily="ui-sans-serif, system-ui">
          ANSWER SHEET
        </text>
        <text x="16" y="44" fontSize="6.5" fill="var(--muted-foreground)"
          fontFamily="ui-sans-serif, system-ui">
          {name}
        </text>
        <line x1="14" y1="50" x2="186" y2="50" stroke="var(--border)" strokeWidth="1" />

        {/* roll grid */}
        <text x="16" y="62" fontSize="5.5" fontWeight="600" fill="var(--muted-foreground)"
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
                stroke={filled ? tint : "var(--border)"}
                strokeWidth="0.8"
              />
            )
          })
        )}

        {/* answer rows */}
        <motion.g
          initial={false}
          animate={animate ? "show" : "hidden"}
          variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06, delayChildren: 0.15 } } }}
        >
          {answers.slice(0, ROWS).map((marked, row) => {
            const y = 72 + row * 16
            return (
              <g key={row}>
                <text x="64" y={y + 2} fontSize="6" fill="var(--muted-foreground)"
                  fontFamily="ui-sans-serif, system-ui" textAnchor="end">
                  {row + 1}
                </text>
                {Array.from({ length: OPTS }).map((_, opt) => {
                  const cx = 80 + opt * 21
                  const isMarked = opt === marked
                  return (
                    <g key={opt}>
                      <circle cx={cx} cy={y} r="5.2" fill="none"
                        stroke="var(--border)" strokeWidth="1" />
                      {isMarked && (
                        <motion.circle
                          cx={cx} cy={y} r="4.4" fill={tint}
                          variants={{
                            hidden: { scale: 0, opacity: 0 },
                            show: { scale: 1, opacity: 1, transition: { type: "spring", stiffness: 420, damping: 18 } },
                          }}
                          style={{ transformBox: "fill-box", transformOrigin: "center" }}
                        />
                      )}
                    </g>
                  )
                })}
              </g>
            )
          })}
        </motion.g>

        {/* footer barcode */}
        <g opacity="0.5">
          {Array.from({ length: 26 }).map((_, i) => (
            <rect key={i} x={16 + i * 2.4} y="225" width={i % 3 === 0 ? 1.6 : 0.8} height="9"
              fill="var(--foreground)" />
          ))}
        </g>

        {/* scan line sweep */}
        {scanning && !reduce && (
          <motion.g
            initial={{ y: 0 }}
            animate={{ y: [56, 200, 56] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          >
            <rect x="8" y="-7" width="184" height="14" fill={tint} opacity="0.14" />
            <rect x="8" y="0" width="184" height="2" fill={tint} />
          </motion.g>
        )}

        {/* graded overlay */}
        {graded && (
          <motion.g
            initial={reduce ? false : { scale: 0.6, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ type: "spring", stiffness: 300, damping: 16, delay: 0.2 }}
          >
            <rect x="116" y="92" width="70" height="34" rx="8" fill="var(--card)"
              stroke={tint} strokeWidth="1.5" />
            <circle cx="130" cy="109" r="7" fill={tint} />
            <path d="M126.5 109 L129 111.5 L133.5 106.5" stroke="var(--card)" strokeWidth="1.6"
              fill="none" strokeLinecap="round" strokeLinejoin="round" />
            <text x="142" y="112" fontSize="10" fontWeight="700" fill="var(--foreground)"
              fontFamily="ui-sans-serif, system-ui">
              {score}
            </text>
          </motion.g>
        )}
      </svg>
    </div>
  )
}
