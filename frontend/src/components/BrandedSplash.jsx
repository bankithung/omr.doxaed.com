/**
 * BrandedSplash — a minimal, clean loading fallback for PUBLIC / auth / landing
 * routes (where the app shell skeleton would be wrong). A centered "DoxaEd OMR"
 * wordmark over a subtle, reduced-motion-safe pulse — never a bare "Loading…"
 * string. Flat + on-theme (gunmetal background, amber OMR accent token).
 */
export default function BrandedSplash() {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className="flex min-h-screen flex-col items-center justify-center gap-5 bg-background text-foreground"
    >
      <span className="flex items-baseline gap-1.5" aria-label="DoxaEd OMR, loading">
        <span className="text-lg font-semibold tracking-tight">DoxaEd</span>
        <span className="font-mono text-xs font-medium uppercase tracking-[0.28em] text-indigo">OMR</span>
      </span>
      {/* subtle indeterminate bar — calm under reduced motion */}
      <span className="relative h-1 w-32 overflow-hidden rounded-full bg-surface-2">
        <span className="absolute inset-y-0 left-0 w-1/3 animate-pulse rounded-full bg-primary motion-reduce:animate-none" />
      </span>
      <span className="sr-only">Loading…</span>
    </div>
  )
}
