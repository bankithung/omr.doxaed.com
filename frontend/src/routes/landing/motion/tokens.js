// Motion tokens — ONE source of truth for the cinematic landing.
// Reference these everywhere; never inline magic numbers. JS (not TS) per project stack.
// See storyboard-tmp.md §1.

// Easing curves (cubic-bezier control points).
export const ease = {
  out: [0.16, 1, 0.3, 1], // expo-out — the premium entrance/reveal
  outSoft: [0.22, 1, 0.36, 1], // gentler quint-out for big hero blocks
  inOut: [0.65, 0, 0.35, 1], // on-screen moves, clip wipes
  inFast: [0.55, 0, 1, 0.45], // exits (snappy)
}

export const spring = {
  snappy: { type: "spring", stiffness: 400, damping: 32, mass: 0.8 }, // buttons, taps, magnetic
  smooth: { type: "spring", stiffness: 200, damping: 30, mass: 1 }, // cards, panels, tilt
  gentle: { type: "spring", stiffness: 120, damping: 24, mass: 1 }, // large hero blocks
  bouncy: { type: "spring", duration: 0.5, bounce: 0.22 }, // playful accents only
  // For useSpring() wrapping scroll values — the master scrub feel:
  scroll: { stiffness: 90, damping: 30, restDelta: 0.001, mass: 0.4 },
}

export const dur = { micro: 0.12, ui: 0.2, enter: 0.4, exit: 0.24, hero: 0.6 }

// Stagger discipline: 30–60ms = "a hand of cards"; >80ms = slideshow; <20ms = simultaneous.
export const stagger = {
  tight: 0.03,
  base: 0.04,
  loose: 0.06,
  words: 0.05,
  chars: 0.025,
}

// ── Landing palette (explicit colors — NOT app theme tokens). Dark cinematic. ──
// Indigo primary ~ oklch(0.488 0.243 264.376) ≈ #4f46e5, teal/cyan secondary,
// grade-band emerald/amber/rose for analytics + aurora.
export const palette = {
  bg: "#05060a", // near-black canvas
  bgSoft: "#0a0c14",
  panel: "rgba(255,255,255,0.04)",
  panelSolid: "#0f1120",
  border: "rgba(255,255,255,0.10)",
  borderStrong: "rgba(255,255,255,0.18)",
  text: "#f5f6fb",
  textMuted: "rgba(226,229,245,0.62)",
  textFaint: "rgba(226,229,245,0.40)",
  indigo: "#6366f1",
  indigoDeep: "#4f46e5",
  teal: "#2dd4bf",
  cyan: "#38bdf8",
  emerald: "#34d399",
  amber: "#fbbf24",
  rose: "#fb7185",
}

// rgba glow strings used by spotlights/auroras.
export const glow = {
  indigo: "rgba(99,102,241,0.55)",
  indigoSoft: "rgba(99,102,241,0.18)",
  teal: "rgba(45,212,191,0.45)",
  tealSoft: "rgba(45,212,191,0.16)",
  cyan: "rgba(56,189,248,0.20)",
  emerald: "rgba(52,211,153,0.18)",
  amber: "rgba(251,191,36,0.16)",
  rose: "rgba(251,113,133,0.16)",
}
