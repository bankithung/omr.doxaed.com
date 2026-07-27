import MaterialIcon from "./MaterialIcon"

// Real product trust points (reused from the footer copy).
const TRUST_POINTS = [
  "Server-side grading",
  "Auditable results",
  "Encrypted student PII",
  "Per-organisation data isolation",
  "Works with any phone or scanner",
  "Never guessed, low-confidence reads go to review",
]

function TrustItem({ children }) {
  return (
    <span className="flex shrink-0 items-center gap-2 px-6 text-sm text-muted-foreground">
      <MaterialIcon name="task" className="size-4 shrink-0 text-indigo" />
      {children}
    </span>
  )
}

/**
 * TrustStrip — a CSS marquee (40s linear infinite, edge-fade mask, pause on
 * hover) of real product trust points. The track is duplicated so the loop is
 * seamless; the `landing-marquee` keyframes live in index.css. Reduced-motion
 * users get a static, wrapped strip via the prefers-reduced-motion backstop in
 * index.css (animation paused / wrap allowed).
 */
export default function TrustStrip() {
  return (
    <div className="border-y border-border bg-card/40 py-5">
      <div className="landing-marquee-mask group relative mx-auto flex max-w-[90rem] overflow-hidden">
        <div className="landing-marquee flex min-w-full shrink-0 items-center" aria-hidden="false">
          {TRUST_POINTS.map((t) => (
            <TrustItem key={t}>{t}</TrustItem>
          ))}
        </div>
        <div className="landing-marquee flex min-w-full shrink-0 items-center" aria-hidden="true">
          {TRUST_POINTS.map((t) => (
            <TrustItem key={`dup-${t}`}>{t}</TrustItem>
          ))}
        </div>
      </div>
    </div>
  )
}
