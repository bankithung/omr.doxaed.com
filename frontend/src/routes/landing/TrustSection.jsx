import MaterialIcon from "./MaterialIcon"
import { ScanSheet } from "./ProductGraphics"
import SectionContainer from "./SectionContainer"
import { Reveal, RevealItem, FadeInUp } from "./motion/reveal"

// Real platform guarantees only — no invented certifications or claims.
const TRUST = [
  {
    icon: "shield",
    title: "Server-side grading",
    body: "Every sheet is graded against its own stored answer key on the server — never in the browser — so a score can't be tampered with client-side.",
  },
  {
    icon: "task",
    title: "Never guessed",
    body: "Faint, double-marked or missing reads are routed to a review queue with the cropped bubble image, not silently guessed.",
  },
  {
    icon: "lock",
    title: "Encrypted student PII",
    body: "Names and roll numbers are encrypted at rest; only what a public result needs is ever exposed on the portal.",
  },
  {
    icon: "folder",
    title: "Owner-scoped & auditable",
    body: "Every test, sheet and result belongs to one owner or organisation. Access is role-checked and grading actions are auditable.",
  },
]

/**
 * TrustSection — the "Why DoxaEd OMR" trust band: real platform guarantees
 * (server-side grading, never-guessed review queue, encrypted PII, owner-scoped
 * & auditable) beside an animated scan/review graphic. fadeInUp staggered
 * reveal. Flat, app tokens, theme-aware.
 */
export default function TrustSection() {
  return (
    <SectionContainer id="why" className="border-t border-border">
      <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2 lg:gap-16">
        <div>
          <FadeInUp>
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Why DoxaEd OMR
            </span>
            <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              Grading you can defend
            </h2>
            <p className="mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              Results that hold up to scrutiny: every score is computed server-side,
              every uncertain read is reviewed, and every record is owned and auditable.
            </p>
          </FadeInUp>

          <Reveal as="ul" className="mt-8 grid gap-4 sm:grid-cols-2">
            {TRUST.map((t) => (
              <RevealItem as="li" key={t.title} className="rounded-xl border border-border bg-card p-5">
                <span className="flex size-9 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                  <MaterialIcon name={t.icon} className="size-[18px]" />
                </span>
                <h3 className="mt-3 text-sm font-medium text-foreground">{t.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{t.body}</p>
              </RevealItem>
            ))}
          </Reveal>
        </div>

        <FadeInUp delay={0.1} className="lg:pl-4">
          <ScanSheet />
          <p className="mt-3 text-center font-mono text-[11px] text-muted-foreground">
            Low-confidence reads go to review — never a guess.
          </p>
        </FadeInUp>
      </div>
    </SectionContainer>
  )
}
