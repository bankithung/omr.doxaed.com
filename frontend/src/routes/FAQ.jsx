import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * FAQ — a dedicated, grouped question-and-answer page using Pricing's exact
 * Accordion pattern. Four real categories (Product, Grading, Data & privacy,
 * Getting started & billing). Every answer describes how the product actually
 * works — students fill paper (no app), scans align via QR + fiducials, grading
 * uses each sheet's stored key with a review queue, PII is encrypted and
 * owner-scoped. No invented metrics, SLAs or claims.
 */

const CATEGORIES = [
  {
    icon: "checklist",
    group: "Product",
    intro: "What DoxaEd OMR is and how a test reaches a student.",
    items: [
      {
        q: "What is OMR, and what does DoxaEd OMR do?",
        a: "OMR — optical mark recognition — is reading the filled bubbles on a paper answer sheet automatically. DoxaEd OMR generates shuffled bubble sheets for a test, lets you scan the filled sheets, and auto-grades them against each sheet's stored answer key — producing results, analytics and report cards.",
      },
      {
        q: "Do students need an app or an account?",
        a: "No. Students do nothing digital. They fill a printed paper answer sheet with a pen or pencil, exactly as they would on any bubble exam. Only the teacher or centre uses DoxaEd OMR — to generate the sheets and to scan them afterwards.",
      },
      {
        q: "How are sheets scanned?",
        a: "From any phone camera or document scanner. Each sheet carries a QR code identity and fiducial alignment markers, so a photo is aligned and the bubbles are read from the correct positions regardless of which device captured it.",
      },
      {
        q: "What can students fill — how many options?",
        a: "Sheets support standard MCQ with 4 or 5 options, sectional and competitive-style papers, and roster pre-bubbled roll numbers for auto-identification. The mode is chosen when you create the test.",
      },
    ],
  },
  {
    icon: "shield",
    group: "Grading",
    intro: "How a filled sheet becomes a trustworthy score.",
    items: [
      {
        q: "How is grading done — and can it be tampered with?",
        a: "Grading happens on the server against that sheet's own stored answer key, never in the browser. Because the score isn't computed on the client, it can't be tampered with client-side, and every result traces back to the key the sheet was generated with.",
      },
      {
        q: "What happens to a bubble that's faint or double-marked?",
        a: "It is never guessed. Low-confidence reads — faint, smudged, double-marked or empty — are routed to a review queue with the cropped image of that bubble, so a human makes the final call. A grade is either confidently read or explicitly reviewed.",
      },
      {
        q: "Does each student get a different sheet?",
        a: "Yes — per-student shuffle generates a unique question (and option) order per student to deter copying, while every sheet is still graded against its own stored key. Shuffling never changes how a sheet is scored.",
      },
      {
        q: "Can I use negative marking or custom multi-mark rules?",
        a: "Yes. Marking rules are configurable per test — including negative marking and how multi-mark (more than one bubble) situations are scored — so competitive and sectional papers grade the way your exam expects.",
      },
      {
        q: "What counts as a \"scan\" for plan limits?",
        a: "One scan is one answer sheet processed by the grader. Your monthly scan allowance counts each sheet you scan and auto-grade within the calendar month. See the plan limits on the pricing page.",
      },
    ],
  },
  {
    icon: "lock",
    group: "Data & privacy",
    intro: "Who can see student data, and how it's protected.",
    items: [
      {
        q: "Is student data encrypted?",
        a: "Student names and roll numbers are encrypted at rest. You upload only the student data you choose, and you remain the controller of your students' data.",
      },
      {
        q: "Can another account see my tests or students?",
        a: "No. Every test, sheet, roster and result belongs to exactly one owner — a user or an organisation — and access is role-checked on every request. There is no path for one account to read another's data.",
      },
      {
        q: "What is exposed on the public result portal?",
        a: "Only the minimal fields a result actually needs are surfaced on the public result portal — never a student's full record. The rest stays scoped to its owner.",
      },
    ],
  },
  {
    icon: "bolt",
    group: "Getting started & billing",
    intro: "Setting up, pricing, and where to get help.",
    items: [
      {
        q: "How do I get started?",
        a: "Create a free account, set up a class and question bank, add your roster, then generate and print shuffled sheets. After the exam you scan and publish. The step-by-step flow is on the Help page.",
      },
      {
        q: "Is there a free plan, and what does it cost?",
        a: "Yes — there's a genuinely free plan for a single tutor running weekly tests, with paid tiers as your batches grow. Full prices and limits are on the pricing page.",
      },
      {
        q: "Where can I get help if I'm stuck?",
        a: "Start with the Help page's getting-started walkthrough. If you still need a hand, contact us and we'll get back to you.",
      },
    ],
  },
]

export default function FAQ() {
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
              FAQ
            </span>
            <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Questions, <span className="text-primary">answered honestly</span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              How DoxaEd OMR actually works — from what students fill on paper to
              how a scan becomes a trustworthy, auditable result.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Grouped Q&A ────────────────────────────────────────────────────── */}
      <SectionContainer className="pt-0">
        <div className="mx-auto max-w-3xl space-y-12">
          {CATEGORIES.map((cat) => (
            <FadeInUp key={cat.group}>
              <div className="flex items-center gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                  <MaterialIcon name={cat.icon} className="size-[18px]" />
                </span>
                <div>
                  <h2 className="text-lg font-medium tracking-tight text-foreground">{cat.group}</h2>
                  <p className="text-sm text-muted-foreground">{cat.intro}</p>
                </div>
              </div>

              <Accordion
                type="single"
                collapsible
                className="mt-5 rounded-xl border border-border bg-card px-5"
              >
                {cat.items.map((item) => (
                  <AccordionItem key={item.q} value={item.q} className="border-border">
                    <AccordionTrigger className="text-left text-base font-medium text-foreground hover:no-underline">
                      {item.q}
                    </AccordionTrigger>
                    <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                      {item.a}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </FadeInUp>
          ))}
        </div>
      </SectionContainer>

      {/* ── Still have questions ───────────────────────────────────────────── */}
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
            <RevealItem as="h2" className="text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
              Still have a question?
            </RevealItem>
            <RevealItem as="p" className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              Walk through setup on the Help page, compare plans on pricing, or
              reach out and we'll help you decide if it fits your tests.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/help">Getting started</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/pricing">See pricing</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
