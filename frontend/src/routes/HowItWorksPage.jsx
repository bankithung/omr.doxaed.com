import { Link } from "react-router-dom"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { DealOut, ScanSheet, AnalyticsChart } from "@/routes/landing/ProductGraphics"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * HowItWorksPage (/how-it-works) — the dedicated deep-dive. The landing carries a
 * compact 4-step teaser; this page explains each module precisely (short copy +
 * three concrete points) paired with the SAME flat animated product graphics the
 * landing uses (they self-animate on scroll via InViewAnim, reduced-motion-safe).
 * Honest content only — every point is a real product behaviour.
 */

const MODULES = [
  {
    n: "01",
    label: "Generate",
    icon: "shuffle",
    title: "One bank, one roster, a unique sheet per student",
    body: "Write your MCQs once and pick a roster. DoxaEd OMR shuffles the question and option order uniquely for every student, then prints a sheet that carries its own answer key and a QR code.",
    points: [
      "Per-student shuffle, neighbours never share an order",
      "Each sheet stores its own answer key",
      "QR identity + corner fiducials printed on every sheet",
    ],
    graphic: <DealOut />,
  },
  {
    n: "02",
    label: "Scan",
    icon: "scan",
    title: "Snap the stack from any phone or scanner",
    body: "Upload photos or scans, no special hardware. Each sheet auto-aligns from its QR code and fiducial markers, so bubbles are read from the exact right positions even from a quick phone photo.",
    points: [
      "Works with any phone camera or office scanner",
      "Auto-aligned by QR + fiducials, no manual cropping",
      "Batch a whole class in a single pass",
    ],
    graphic: <ScanSheet />,
  },
  {
    n: "03",
    label: "Grade",
    icon: "shield",
    title: "Graded server-side against the stored key, never guessed",
    body: "Grading runs on the server against each sheet's own key, so a score can't be computed or tampered with in the browser. Faint or double-marked bubbles aren't guessed, they go to a review queue with the cropped image for you to confirm.",
    points: [
      "Server-side, keyed grading, tamper-resistant",
      "Low-confidence reads → review queue, with the bubble image",
      "Configurable multi-mark & negative-marking rules",
    ],
    graphic: <ScanSheet variant="full" />,
  },
  {
    n: "04",
    label: "Analyse & share",
    icon: "analytics",
    title: "Every test becomes a full analytics profile",
    body: "The whole class is graded and analysed the same evening. See score distributions, toppers, the hardest questions and per-topic mastery, then publish a public result portal and print two-page report cards.",
    points: [
      "Distributions, toppers, item analysis & per-topic mastery",
      "Two-page printable report cards",
      "Shareable public result portal, students check their own",
    ],
    graphic: <AnalyticsChart label="Class score distribution" />,
  },
]

function Module({ n, label, icon, title, body, points, graphic, flip }) {
  return (
    <SectionContainer className="border-t border-border">
 <div className="mx-auto grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
        <FadeInUp className={cn(flip && "lg:order-2")}>
          <span className="inline-flex items-center gap-2 font-mono text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <span className="flex size-7 items-center justify-center rounded-md border border-border bg-surface-2 text-indigo">
              <MaterialIcon name={icon} className="size-4" />
            </span>
            {n} · {label}
          </span>
          <h2 className="mt-4 text-2xl font-medium tracking-tight text-foreground sm:text-3xl">
            {title}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">{body}</p>
          <ul className="mt-6 space-y-3">
            {points.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-sm text-foreground">
                <MaterialIcon name="task" className="mt-0.5 size-4 shrink-0 text-indigo" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </FadeInUp>

        <div className={cn(flip && "lg:order-1")}>{graphic}</div>
      </div>
    </SectionContainer>
  )
}

export default function HowItWorksPage() {
  return (
    <PublicLayout>
      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px]"
          style={{
            background:
              "radial-gradient(55% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 12%, transparent), transparent 72%)",
          }}
        />
        <SectionContainer className="pt-14 pb-6 text-center sm:pt-16">
 <FadeInUp className="mx-auto ">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              How it works
            </span>
 <h1 className="mx-auto mt-3 text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              From a class list to graded{" "}
              <span className="text-indigo">analytics</span>
            </h1>
 <p className="mx-auto mt-5 text-base text-muted-foreground sm:text-lg">
              Four steps, generate, scan, grade, analyse. Here is exactly what
              happens at each one, and why the result holds up to scrutiny.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Modules ────────────────────────────────────────────────────────── */}
      {MODULES.map((m, i) => (
        <Module key={m.n} {...m} flip={i % 2 === 1} />
      ))}

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
 <Reveal className="mx-auto text-center">
            <RevealItem as="h2" className="text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              See the whole loop on your next test
            </RevealItem>
 <RevealItem as="p" className="mx-auto mt-4 text-base text-muted-foreground sm:text-lg">
              Generate, scan and grade a real exam in minutes, free to start, no
              card required.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/help">Read the getting-started guide</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
