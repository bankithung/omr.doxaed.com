import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { DealOut, ScanSheet, AnalyticsChart } from "@/routes/landing/ProductGraphics"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * Features — a deep-dive of the REAL DoxaEd OMR capabilities, grouped into four
 * themed sections (Generate · Scan & grade · Analyse & share · Teams &
 * governance). Each section pairs short benefit copy with the landing's animated
 * product graphics (DealOut / ScanSheet / AnalyticsChart) where they fit, then a
 * grid of the concrete capabilities. Real content only — every capability listed
 * exists in the product (per the landing + app surfaces). Flat, amber brand
 * accent, fadeInUp reveals, mobile-first.
 */

const GENERATE = [
  { icon: "checklist", title: "One question bank", body: "Write MCQs once and reuse them across tests and sections — no re-typing per paper." },
  { icon: "shuffle", title: "Per-student shuffle", body: "Question and option order is shuffled uniquely per student; each sheet stores its own answer key, so copying is pointless and grading stays exact." },
  { icon: "groups", title: "Roster pre-bubbled roll", body: "Start from a class list — sheets carry a pre-bubbled roll grid so students are auto-identified on scan, name or count only." },
  { icon: "target", title: "Competitive / sectional", body: "NEET- and UPSC-style sectional papers with configurable multi-mark and negative-marking rules — 4 or 5 options." },
  { icon: "layers", title: "Shuffled question papers", body: "Generate the matching shuffled question paper alongside each sheet, so the printed exam aligns with its unique answer key." },
  { icon: "devices", title: "Batch sheet generation", body: "Generate a whole batch at once — one bank and one roster fan out into a unique sheet for every student." },
]

const SCAN = [
  { icon: "scan", title: "Scan from any device", body: "Phone photos, a flatbed scanner, or a stack of images — sheets are auto-aligned by corner fiducials and a QR code." },
  { icon: "shield", title: "Server-side auto-grading", body: "Every sheet is graded against its own stored answer key on the server — never in the browser — so a score can't be tampered with client-side." },
  { icon: "task", title: "Review queue — never guessed", body: "Faint, double-marked or missing reads are routed to a review queue with the cropped bubble image, not silently guessed." },
  { icon: "checklist", title: "Inline scan correction", body: "Fix a misread bubble directly on the scan and re-grade — without re-scanning the whole stack." },
  { icon: "bolt", title: "Configurable multi-mark rules", body: "Decide how double-marks and blanks are scored per test, including negative marking for competitive formats." },
]

const ANALYSE = [
  { icon: "analytics", title: "Analytics & item analysis", body: "Score distributions, toppers, the hardest questions and per-topic accuracy — every test becomes a full analytics profile." },
  { icon: "stats", title: "Two-page report cards", body: "Generate clean two-page report cards per student, ready to print or share with parents." },
  { icon: "folder", title: "Public result portal", body: "Publish a public result link per test so students and parents can look up scores — exposing only what a result needs." },
  { icon: "percent", title: "Per-student improvement", body: "Track how a student moves across tests, with percentiles and per-topic mastery over time." },
]

const TEAMS = [
  { icon: "folder", title: "Folders & sharing", body: "Organise tests into folders and share them across your team, with everything scoped to its owner." },
  { icon: "groups", title: "Organisations & roles", body: "Invite members into an organisation with roles, so a coaching centre or school can collaborate under one account." },
  { icon: "lock", title: "Encrypted student PII", body: "Names and roll numbers are encrypted at rest; every test, sheet and result belongs to one owner or organisation." },
  { icon: "task", title: "Auditable grading", body: "Grading actions are role-checked and auditable, so results hold up to scrutiny." },
]

function CapabilityCard({ icon, title, body }) {
  return (
    <RevealItem className="flex h-full gap-4 rounded-xl border border-border bg-card p-5 transition-colors hover:border-border-strong">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
        <MaterialIcon name={icon} className="size-5" />
      </span>
      <div>
        <h3 className="text-base font-medium text-foreground">{title}</h3>
        <p className="mt-1.5 text-sm text-muted-foreground">{body}</p>
      </div>
    </RevealItem>
  )
}

/**
 * FeatureSection — a themed block: eyebrow + heading + benefit copy + an animated
 * landing graphic, beside a grid of capability cards. `flip` puts the graphic on
 * the opposite side at lg for visual rhythm.
 */
function FeatureSection({ id, eyebrow, title, body, items, graphic, caption, flip, bordered = true }) {
  return (
    <SectionContainer id={id} className={bordered ? "border-t border-border" : ""}>
      <FadeInUp className="mx-auto max-w-2xl text-center">
        <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          {eyebrow}
        </span>
        <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">{title}</h2>
        <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">{body}</p>
      </FadeInUp>

      <div className="mx-auto mt-12 grid max-w-6xl items-center gap-10 lg:grid-cols-2 lg:gap-12">
        <FadeInUp delay={0.05} className={flip ? "lg:order-2" : ""}>
          {graphic}
          {caption && (
            <p className="mt-3 text-center font-mono text-[11px] text-muted-foreground">{caption}</p>
          )}
        </FadeInUp>

        <Reveal as="div" className={["grid gap-4 sm:grid-cols-2", flip ? "lg:order-1" : ""].join(" ")}>
          {items.map((it) => (
            <CapabilityCard key={it.title} {...it} />
          ))}
        </Reveal>
      </div>
    </SectionContainer>
  )
}

export default function Features() {
  return (
    <PublicLayout>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px]"
          style={{
            background:
              "radial-gradient(55% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 12%, transparent), transparent 72%)",
          }}
        />
        <SectionContainer className="pt-14 pb-8 sm:pt-16 text-center">
          <FadeInUp className="mx-auto max-w-2xl">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Features
            </span>
            <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Everything to generate, scan, grade & <span className="text-primary">analyse</span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              One bank, one roster, a unique shuffled sheet for every student —
              scanned, server-side auto-graded, and turned into analytics. Here is
              what that loop actually does.
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-5 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-5 text-sm">
                <Link to="/pricing">See pricing</Link>
              </Button>
            </div>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Generate ───────────────────────────────────────────────────────── */}
      <FeatureSection
        id="generate"
        eyebrow="Generate"
        title="Unique, shuffled sheets for every student"
        body="From a class list to a stack of one-of-a-kind answer sheets — each with its own stored key and a QR code, so the same exam never has two identical papers."
        items={GENERATE}
        graphic={<DealOut />}
        caption="One bank + one roster → many shuffled sheets."
        bordered={false}
      />

      {/* ── Scan & grade ───────────────────────────────────────────────────── */}
      <FeatureSection
        id="scan"
        eyebrow="Scan & grade"
        title="Scan a stack, grade it server-side"
        body="Upload from any phone or scanner. Sheets auto-align, grade against their own keys on the server, and route every uncertain read to review — never a guess."
        items={SCAN}
        graphic={<ScanSheet />}
        caption="Low-confidence reads go to review — never guessed."
        flip
      />

      {/* ── Analyse & share ────────────────────────────────────────────────── */}
      <FeatureSection
        id="analyse"
        eyebrow="Analyse & share"
        title="Every test becomes an analytics profile"
        body="Distributions, toppers, the hardest questions, item analysis and per-topic mastery — plus two-page report cards and a public result portal."
        items={ANALYSE}
        graphic={<AnalyticsChart label="Class score distribution" />}
        caption="Score distributions, toppers and the hardest questions."
      />

      {/* ── Teams & governance ─────────────────────────────────────────────── */}
      <SectionContainer id="teams" className="border-t border-border">
        <FadeInUp className="mx-auto max-w-2xl text-center">
          <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Teams &amp; governance
          </span>
          <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            Built for teams, scoped by owner
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
            Folders, organisations and roles let a centre or school collaborate —
            while encryption and owner-scoping keep every record isolated and
            auditable.
          </p>
        </FadeInUp>

        <Reveal as="div" className="mx-auto mt-12 grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TEAMS.map((it) => (
            <CapabilityCard key={it.title} {...it} />
          ))}
        </Reveal>
      </SectionContainer>

      {/* ── CTA ────────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-t border-border">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              "radial-gradient(50% 60% at 50% 50%, color-mix(in oklch, var(--color-primary) 10%, transparent), transparent 70%)",
          }}
        />
        <SectionContainer>
          <Reveal className="mx-auto max-w-2xl text-center">
            <RevealItem>
              <span className="mx-auto flex size-12 items-center justify-center rounded-xl border border-border bg-card text-primary">
                <MaterialIcon name="layers" className="size-6" />
              </span>
            </RevealItem>
            <RevealItem as="h2" className="mx-auto mt-6 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              See it on your next exam.
            </RevealItem>
            <RevealItem as="p" className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              Create your first test free — generate shuffled sheets, scan from
              your phone, and get graded analytics the same evening.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/pricing">Compare plans</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
