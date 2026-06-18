import { useEffect, useRef, useState } from "react"
import {
  motion,
  useTransform,
  useScroll,
  useVelocity,
  useSpring,
  useReducedMotion,
  frame,
  cancelFrame,
} from "framer-motion"
import { usePointerFine } from "./Micro"

/**
 * FlowSpine — the cinematic connective tissue of the pinned centerpiece.
 *
 * Curved bezier "data pipes" that get DRAWN by a travelling comet head as the
 * shared scroll progress `p` advances, with a multi-layer bloom (wide soft glow
 * under + crisp gradient stroke on top + bright comet tip), then carry a LIVE
 * stream of glowing particles flowing source → destination once drawn. Speed of
 * the particle flow is subtly tied to scroll velocity. Everything is a pure
 * function of `p` (bidirectional / rewinds on scroll-up) using only
 * pathLength / opacity / transform.
 *
 *   Act 1 (≈0.02–0.22): roster + bank pipes converge into the merge node.
 *   Act 2 (≈0.28–0.50): the node fans light beams out to each shuffled sheet.
 *
 * A single <canvas> draws all flowing particles (perf: one paint, not N nodes).
 * Disabled / static under prefers-reduced-motion.
 *
 * Desktop (landscape) uses the wide horizontal layout; on narrow screens a clean
 * vertical curved variant is used so the pipes never cross awkwardly.
 */

// ── geometry (viewBox 0 0 1000 1000, slice-fit) ───────────────────────────────
const NODE = { x: 500, y: 470 }

// Horizontal (desktop) source endpoints + control points for gentle arcs.
const H_SOURCES = [
  { from: [150, 410], c1: [300, 360], c2: [360, 470] }, // roster (left)
  { from: [850, 410], c1: [700, 360], c2: [640, 470] }, // bank (right)
]
// Vertical (mobile) source endpoints — stacked, arc into the node from top.
const V_SOURCES = [
  { from: [320, 230], c1: [360, 360], c2: [470, 400] },
  { from: [680, 230], c1: [640, 360], c2: [530, 400] },
]

function convergePath(s) {
  return `M ${s.from[0]} ${s.from[1]} C ${s.c1[0]} ${s.c1[1]}, ${s.c2[0]} ${s.c2[1]}, ${NODE.x} ${NODE.y}`
}

// Fan beams sweep from the node out/down to each sheet position.
function fanPaths(n, vertical) {
  return Array.from({ length: n }).map((_, i) => {
    const spread = i - (n - 1) / 2
    const tx = NODE.x + spread * (vertical ? 36 : 62)
    const ty = NODE.y + (vertical ? 250 : 150) + Math.abs(spread) * (vertical ? 6 : 10)
    // bow the beam outward like a light ray
    const cx = NODE.x + spread * (vertical ? 50 : 90)
    const cy = NODE.y + (vertical ? 130 : 70)
    return `M ${NODE.x} ${NODE.y} Q ${cx} ${cy}, ${tx} ${ty}`
  })
}

// Sample a quadratic/cubic-ish path's point set for the particle canvas.
// We re-derive points from the same control points (cheap, deterministic).
function sampleCubic(p0, c1, c2, p1, steps = 40) {
  const pts = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const mt = 1 - t
    const x =
      mt * mt * mt * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t * t * t * p1[0]
    const y =
      mt * mt * mt * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t * t * t * p1[1]
    pts.push([x, y])
  }
  return pts
}
function sampleQuad(p0, c, p1, steps = 36) {
  const pts = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const mt = 1 - t
    const x = mt * mt * p0[0] + 2 * mt * t * c[0] + t * t * p1[0]
    const y = mt * mt * p0[1] + 2 * mt * t * c[1] + t * t * p1[1]
    pts.push([x, y])
  }
  return pts
}

// ── A single bloom pipe with a comet head riding the drawn tip ─────────────────
function Pipe({ d, draw, pts, gradId, width = 2.4, headColor = "#7dd3fc" }) {
  // Comet head rides the drawn tip. Position is derived from the sampled path
  // points (works in every browser; no reliance on CSS offset-path support).
  const headOpacity = useTransform(draw, [0, 0.04, 0.9, 1], [0, 1, 1, 0])
  const hx = useTransform(draw, (v) => {
    const seg = Math.min(1, v) * (pts.length - 1)
    const i = Math.min(pts.length - 2, Math.floor(seg))
    const f = seg - i
    return pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f
  })
  const hy = useTransform(draw, (v) => {
    const seg = Math.min(1, v) * (pts.length - 1)
    const i = Math.min(pts.length - 2, Math.floor(seg))
    const f = seg - i
    return pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
  })
  return (
    <g>
      {/* wide soft bloom under-copy */}
      <motion.path
        d={d} fill="none" stroke={`url(#${gradId})`} strokeWidth={width * 3.6}
        strokeLinecap="round" style={{ pathLength: draw, filter: "blur(7px)", opacity: 0.32 }}
      />
      {/* crisp gradient stroke */}
      <motion.path
        d={d} fill="none" stroke={`url(#${gradId})`} strokeWidth={width}
        strokeLinecap="round" style={{ pathLength: draw }}
      />
      {/* comet leading head — bright glow dot riding the path tip */}
      <motion.g style={{ x: hx, y: hy, opacity: headOpacity }}>
        <circle r="9" fill={headColor} opacity="0.25" style={{ filter: "blur(4px)" }} />
        <circle r="3.4" fill="#ffffff" />
        <circle r="6" fill="none" stroke={headColor} strokeWidth="1.5" opacity="0.6" />
      </motion.g>
    </g>
  )
}

export default function FlowSpine({ p, n = 8 }) {
  const reduce = useReducedMotion()
  const fine = usePointerFine()
  const canvasRef = useRef(null)

  // vertical vs horizontal layout — tracked in state (never read a ref in render).
  const [vertical, setVertical] = useState(false)
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return
    const mq = window.matchMedia("(max-width: 640px)")
    const update = () => setVertical(mq.matches)
    update()
    mq.addEventListener?.("change", update)
    return () => mq.removeEventListener?.("change", update)
  }, [])
  const sources = vertical ? V_SOURCES : H_SOURCES

  // draw progress for each act (pure functions of p → bidirectional)
  const drawConverge = useTransform(p, [0.0, 0.2], [0, 1])
  const drawFan = useTransform(p, [0.27, 0.49], [0, 1])
  const spineFade = useTransform(p, [0.0, 0.03, 0.52, 0.6], [0, 1, 1, 0])
  // slight parallax + breathe so the spine feels volumetric, not a 2D overlay
  const spineY = useTransform(p, [0, 0.6], ["1.5%", "-1.5%"])
  const spineScale = useTransform(p, [0, 0.3, 0.6], [1.02, 1, 1.02])

  // scroll velocity → particle speed multiplier (subtle)
  const { scrollY } = useScroll()
  const velocity = useVelocity(scrollY)
  const smoothVel = useSpring(velocity, { stiffness: 200, damping: 40 })

  const convergePts = sources.map((s) => sampleCubic(s.from, s.c1, s.c2, [NODE.x, NODE.y]))
  const fanQuads = fanPaths(n, vertical)
  const fanPts = fanQuads.map((_, i) => {
    const spread = i - (n - 1) / 2
    const tx = NODE.x + spread * (vertical ? 36 : 62)
    const ty = NODE.y + (vertical ? 250 : 150) + Math.abs(spread) * (vertical ? 6 : 10)
    const cx = NODE.x + spread * (vertical ? 50 : 90)
    const cy = NODE.y + (vertical ? 130 : 70)
    return sampleQuad([NODE.x, NODE.y], [cx, cy], [tx, ty])
  })

  // motion-value snapshots read inside the canvas rAF (no React re-render)
  const drawConvergeMV = drawConverge
  const drawFanMV = drawFan
  const fadeMV = spineFade

  // ── live particle canvas — one paint loop driven by framer's frame loop ──────
  useEffect(() => {
    if (reduce) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // size the canvas to its element box (DPR-aware), in the 1000×1000 space.
    let dpr = Math.min(2, window.devicePixelRatio || 1)
    const resize = () => {
      const r = canvas.getBoundingClientRect()
      dpr = Math.min(2, window.devicePixelRatio || 1)
      canvas.width = Math.max(1, Math.round(r.width * dpr))
      canvas.height = Math.max(1, Math.round(r.height * dpr))
    }
    resize()
    window.addEventListener("resize", resize)

    // particles: a phase 0..1 along an assigned polyline
    const PER_CONVERGE = 5
    const PER_FAN = 3
    const particles = []
    convergePts.forEach((pts, ci) => {
      for (let k = 0; k < PER_CONVERGE; k++)
        particles.push({ pts, phase: (k / PER_CONVERGE + ci * 0.13) % 1, kind: "c", line: ci })
    })
    fanPts.forEach((pts, fi) => {
      for (let k = 0; k < PER_FAN; k++)
        particles.push({ pts, phase: (k / PER_FAN + fi * 0.07) % 1, kind: "f", line: fi })
    })

    const lerp = (a, b, t) => a + (b - a) * t
    const pointAt = (pts, t) => {
      const seg = t * (pts.length - 1)
      const i = Math.min(pts.length - 2, Math.floor(seg))
      const f = seg - i
      return [lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)]
    }

    const update = () => {
      const w = canvas.width
      const h = canvas.height
      ctx.clearRect(0, 0, w, h)
      const fade = fadeMV.get()
      if (fade <= 0.01) return
      const sx = w / 1000
      const sy = h / 1000
      const dc = drawConvergeMV.get()
      const df = drawFanMV.get()
      // velocity-tied speed (clamped) + base drift
      const v = Math.min(2.2, Math.abs(smoothVel.get()) / 1400)
      const speed = 0.0016 + v * 0.0026

      ctx.globalCompositeOperation = "lighter"
      for (const part of particles) {
        const gate = part.kind === "c" ? dc : df
        if (gate < 0.05) continue
        part.phase = (part.phase + speed) % 1
        // only show particles within the already-drawn portion of the pipe
        if (part.phase > gate) continue
        const [px, py] = pointAt(part.pts, part.phase)
        const x = px * sx
        const y = py * sy
        const headFade = part.phase > gate - 0.12 ? Math.max(0, (gate - part.phase) / 0.12) : 1
        const a = fade * (part.kind === "c" ? 0.85 : 0.7) * headFade
        const rad = (part.kind === "c" ? 2.6 : 2.1) * dpr
        const col = part.kind === "c" ? "120,200,255" : "129,140,248"
        const g = ctx.createRadialGradient(x, y, 0, x, y, rad * 3)
        g.addColorStop(0, `rgba(${col},${a})`)
        g.addColorStop(1, `rgba(${col},0)`)
        ctx.fillStyle = g
        ctx.beginPath()
        ctx.arc(x, y, rad * 3, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalCompositeOperation = "source-over"
    }

    frame.update(update, true)
    return () => {
      cancelFrame(update)
      window.removeEventListener("resize", resize)
    }
  }, [reduce, n, vertical])

  if (reduce) {
    // static, faint curved pipes — no draw, no particles
    return (
      <svg
        aria-hidden
        viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice"
        className="pointer-events-none absolute inset-0 h-full w-full opacity-40"
      >
        {sources.map((s, i) => (
          <path key={i} d={convergePath(s)} fill="none" stroke="rgba(56,189,248,0.4)" strokeWidth="2" strokeLinecap="round" />
        ))}
      </svg>
    )
  }

  return (
    <motion.div
      aria-hidden
      style={{ opacity: spineFade, y: spineY, scale: spineScale }}
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <svg viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full">
        <defs>
          {/* bright near source → soft at tip, brand indigo→cyan→teal */}
          <linearGradient id="pipeGradL" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="60%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="rgba(45,212,191,0.55)" />
          </linearGradient>
          <linearGradient id="pipeGradR" x1="1" y1="0" x2="0" y2="0">
            <stop offset="0%" stopColor="#2dd4bf" />
            <stop offset="60%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="rgba(99,102,241,0.55)" />
          </linearGradient>
          <linearGradient id="pipeGradFan" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7dd3fc" />
            <stop offset="100%" stopColor="rgba(99,102,241,0.35)" />
          </linearGradient>
        </defs>

        {/* Act 1 — converge pipes */}
        {sources.map((s, i) => (
          <Pipe
            key={i}
            d={convergePath(s)}
            pts={convergePts[i]}
            draw={drawConverge}
            gradId={i === 0 ? "pipeGradL" : "pipeGradR"}
            width={2.6}
            headColor="#7dd3fc"
          />
        ))}

        {/* node halo at the convergence point */}
        <circle cx={NODE.x} cy={NODE.y} r="26" fill="none" stroke="rgba(56,189,248,0.35)" strokeWidth="1" />

        {/* Act 2 — fan beams */}
        {fanQuads.map((d, i) => (
          <Pipe key={`f${i}`} d={d} pts={fanPts[i]} draw={drawFan} gradId="pipeGradFan" width={1.8} headColor="#a5b4fc" />
        ))}
      </svg>

      {/* live particle flow — single canvas overlay (only mounts on capable cursors
          OR touch; cheap enough either way, but skipped under reduced-motion above) */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full"
        style={{ opacity: fine ? 1 : 0.85 }}
      />
    </motion.div>
  )
}
