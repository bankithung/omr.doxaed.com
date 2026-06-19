import { Fragment, useState } from "react"
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
 * Pricing — a Supabase-shaped pricing page built from the REAL seeded plans.
 *
 * Plan source of truth: backend `billing/management/commands/seed_plans.py`
 * (mirrored by `billing/limits.py` + the `GET /api/v1/billing/plans` endpoint
 * in `billing/views.py`). The four tiers — free / team / business / enterprise —
 * and their exact prices (INR/month) + limits (seats, students/generation,
 * generations/day, monthly scans) are reproduced verbatim below. These public
 * pages run logged-out, and the plans endpoint requires auth, so the figures are
 * inlined from the seed (the single source) rather than fetched — kept in sync
 * with the backend. NO invented pricing.
 *
 * Billing is monthly-only in the product (Razorpay subscriptions; no annual
 * price exists in the data). The monthly/yearly toggle is therefore honest: it
 * shows the real monthly price and, on "Yearly", surfaces a truthful note that
 * annual invoicing is available on request — it never fabricates a discounted
 * yearly figure.
 */

// ── Real plan data — verbatim from billing/management/commands/seed_plans.py ──
const PLANS = [
  {
    code: "free",
    name: "Free",
    priceInr: 0,
    tagline: "For a single tutor running weekly tests.",
    cta: { label: "Start free", to: "/register" },
    limits: {
      seats: "1 seat",
      studentsPerGen: "Up to 10 students / sheet generation",
      gensPerDay: "5 sheet generations / day",
      monthlyScans: "100 scans / month",
    },
    features: [
      "All OMR modes (standard, sectional, per-student shuffle)",
      "Scan & auto-grade from any phone or scanner",
      "Review queue for low-confidence reads",
      "Analytics, item analysis & report cards",
      "Public result portal & sharing",
    ],
  },
  {
    code: "team",
    name: "Pro",
    priceInr: 1000,
    tagline: "For a coaching centre grading whole batches.",
    cta: { label: "Get started", to: "/register" },
    popular: true,
    limits: {
      seats: "Up to 5 seats",
      studentsPerGen: "Unlimited students / generation",
      gensPerDay: "Unlimited generations / day",
      monthlyScans: "2,000 scans / month",
    },
    features: [
      "Everything in Free",
      "Organisations, roles & member invites",
      "Per-teacher class & subject access",
      "Higher generation + scan throughput",
      "Audit log of grading actions",
    ],
  },
  {
    code: "business",
    name: "Business",
    priceInr: 2000,
    tagline: "For a school standardising tests across sections.",
    cta: { label: "Get started", to: "/register" },
    limits: {
      seats: "Up to 20 seats",
      studentsPerGen: "Unlimited students / generation",
      gensPerDay: "Unlimited generations / day",
      monthlyScans: "10,000 scans / month",
    },
    features: [
      "Everything in Pro",
      "20 seats for larger teams",
      "10,000 scans / month headroom",
      "Organisation-wide roles & permissions",
      "Priority email support",
    ],
  },
  {
    code: "enterprise",
    name: "Enterprise",
    priceInr: null, // custom — no seeded price
    tagline: "For multi-campus groups with custom needs.",
    cta: { label: "Contact sales", to: "/contact" },
    limits: {
      seats: "Unlimited seats",
      studentsPerGen: "Unlimited students / generation",
      gensPerDay: "Unlimited generations / day",
      monthlyScans: "Unlimited scans",
    },
    features: [
      "Everything in Business",
      "Unlimited seats & scans",
      "Custom onboarding & data agreements",
      "Annual invoicing & procurement support",
      "Dedicated support contact",
    ],
  },
]

// ── Feature-comparison matrix — rows = capability, value per tier ──────────────
// "•" / number = a real value; true = ✓ ; false = ✗. Mirrors the seed limits.
const COMPARE = [
  {
    group: "Limits",
    rows: [
      { label: "Seats", values: ["1", "5", "20", "Unlimited"] },
      { label: "Students per generation", values: ["10", "Unlimited", "Unlimited", "Unlimited"] },
      { label: "Generations per day", values: ["5", "Unlimited", "Unlimited", "Unlimited"] },
      { label: "Scans per month", values: ["100", "2,000", "10,000", "Unlimited"] },
    ],
  },
  {
    group: "OMR & grading",
    rows: [
      { label: "All OMR modes & per-student shuffle", values: [true, true, true, true] },
      { label: "Competitive / sectional papers", values: [true, true, true, true] },
      { label: "Scan & server-side auto-grading", values: [true, true, true, true] },
      { label: "Inline scan correction", values: [true, true, true, true] },
      { label: "Review queue (never guessed)", values: [true, true, true, true] },
      { label: "Configurable multi-mark rules", values: [true, true, true, true] },
    ],
  },
  {
    group: "Analytics & sharing",
    rows: [
      { label: "Analytics & item analysis", values: [true, true, true, true] },
      { label: "Two-page report cards", values: [true, true, true, true] },
      { label: "Public result portal", values: [true, true, true, true] },
      { label: "Folders & sharing", values: [true, true, true, true] },
    ],
  },
  {
    group: "Teams & governance",
    rows: [
      { label: "Organisations & roles", values: [false, true, true, true] },
      { label: "Member invites", values: [false, true, true, true] },
      { label: "Audit log", values: [false, true, true, true] },
      { label: "Custom data agreements", values: [false, false, false, true] },
    ],
  },
]

const FAQ = [
  {
    q: "Is there a free plan?",
    a: "Yes. The Free plan is genuinely free (₹0), with 1 seat, up to 10 students per sheet generation, 5 generations a day and 100 scans a month — enough for a single tutor to run weekly tests. No card is required to start.",
  },
  {
    q: "What counts as a scan?",
    a: "One scan is one answer sheet processed by the grader. Your monthly scan allowance (100 on Free, 2,000 on Pro, 10,000 on Business, unlimited on Enterprise) counts each sheet you scan and auto-grade within the calendar month.",
  },
  {
    q: "Can I change plans?",
    a: "Yes. An organisation admin can upgrade or downgrade at any time from the in-app billing screen. Paid plans are billed monthly via Razorpay; changes take effect for your organisation right away.",
  },
  {
    q: "Do you store student data?",
    a: "Only what you upload, and student names and roll numbers are encrypted at rest. Every test, sheet and result is scoped to one owner or organisation, and only what a public result needs is ever exposed on the portal. You remain the controller of your students' data.",
  },
  {
    q: "What happens when I hit a limit?",
    a: "Nothing is silently dropped. When you reach a plan limit — seats, students per generation, generations per day or monthly scans — the action is blocked with a clear message, and you can upgrade to a higher tier to continue.",
  },
  {
    q: "Do you offer annual billing?",
    a: "Subscriptions bill monthly by default. If you need annual invoicing or procurement support — common for schools and multi-campus groups — contact us and we'll arrange it on the Business or Enterprise tier.",
  },
]

function formatPrice(priceInr) {
  if (priceInr === null) return "Custom"
  if (priceInr === 0) return "Free"
  return `₹${priceInr.toLocaleString("en-IN")}`
}

// ── Custom monthly/yearly toggle (NOT a native control) ────────────────────────
function BillingToggle({ value, onChange }) {
  const options = [
    { id: "monthly", label: "Monthly" },
    { id: "yearly", label: "Yearly" },
  ]
  return (
    <div
      role="radiogroup"
      aria-label="Billing period"
      className="inline-flex items-center gap-1 rounded-full border border-border bg-card p-1"
    >
      {options.map((o) => {
        const active = value === o.id
        return (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.id)}
            className={[
              "inline-flex min-h-[40px] items-center gap-2 rounded-full px-4 text-sm font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {o.label}
            {o.id === "yearly" && (
              <span
                className={[
                  "rounded-full px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.08em]",
                  active ? "bg-primary-foreground/15 text-primary-foreground" : "bg-surface-2 text-primary",
                ].join(" ")}
              >
                on request
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

function Check({ ok }) {
  return ok ? (
    <MaterialIcon name="task" title="Included" className="mx-auto size-4 text-success" />
  ) : (
    <span aria-label="Not included" className="mx-auto block size-4 text-center text-muted-foreground">
      —
    </span>
  )
}

function PlanCard({ plan, billing }) {
  const isPopular = !!plan.popular
  const price = formatPrice(plan.priceInr)
  const showPerMonth = plan.priceInr !== null && plan.priceInr !== 0
  return (
    <RevealItem
      className={[
        "relative flex h-full flex-col rounded-xl border bg-card p-6 transition-colors",
        isPopular
          ? "border-primary ring-1 ring-primary"
          : "border-border hover:border-border-strong",
      ].join(" ")}
    >
      {isPopular && (
        <span className="absolute -top-3 left-6 inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
          <span className="size-1.5 rounded-full bg-primary-foreground" />
          Most popular
        </span>
      )}

      <h3 className="text-base font-medium text-foreground">{plan.name}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{plan.tagline}</p>

      <div className="mt-5 flex items-baseline gap-1.5">
        <span className="text-3xl font-medium tracking-tight tabular text-foreground">{price}</span>
        {showPerMonth && (
          <span className="text-sm text-muted-foreground">/ month</span>
        )}
      </div>
      <p className="mt-1 min-h-[1.25rem] font-mono text-[11px] text-muted-foreground">
        {plan.priceInr === null
          ? "Tailored to your group"
          : billing === "yearly" && showPerMonth
            ? "Billed monthly · annual invoicing on request"
            : plan.priceInr === 0
              ? "No card required"
              : "Billed monthly via Razorpay"}
      </p>

      <Button
        asChild
        variant={isPopular ? "default" : "outline"}
        className="mt-5 h-10 w-full text-sm"
      >
        <Link to={plan.cta.to}>{plan.cta.label}</Link>
      </Button>

      <ul className="mt-5 space-y-2.5 border-t border-border pt-5">
        {Object.values(plan.limits).map((line) => (
          <li key={line} className="flex items-start gap-2 text-sm text-foreground">
            <MaterialIcon name="task" className="mt-0.5 size-3.5 shrink-0 text-primary" />
            <span>{line}</span>
          </li>
        ))}
      </ul>

      <ul className="mt-4 space-y-2.5">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-muted-foreground">
            <MaterialIcon name="task" className="mt-0.5 size-3.5 shrink-0 text-success" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
    </RevealItem>
  )
}

export default function Pricing() {
  const [billing, setBilling] = useState("monthly")

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
        <SectionContainer className="pt-14 pb-10 sm:pt-16 text-center">
          <FadeInUp className="mx-auto max-w-2xl">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Pricing
            </span>
            <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Simple, predictable pricing — <span className="text-primary">scales with you</span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              Start free, then move up as your batches grow. Every plan includes
              the full grading engine — shuffled sheets, server-side auto-grading,
              the review queue and analytics. You only pay for scale.
            </p>
          </FadeInUp>

          <FadeInUp delay={0.1} className="mt-8 flex flex-col items-center gap-2">
            <BillingToggle value={billing} onChange={setBilling} />
            <p className="font-mono text-[11px] text-muted-foreground">
              {billing === "yearly"
                ? "Prices are monthly — ask us about annual invoicing"
                : "Prices in INR, billed per month"}
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Tier cards ─────────────────────────────────────────────────────── */}
      <SectionContainer className="pt-0">
        <Reveal className="mx-auto grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((p) => (
            <PlanCard key={p.code} plan={p} billing={billing} />
          ))}
        </Reveal>
        <FadeInUp className="mx-auto mt-6 max-w-6xl">
          <p className="text-center font-mono text-[11px] text-muted-foreground">
            All limits enforced server-side. Hit one and the action is blocked
            with a clear message — never silently dropped.
          </p>
        </FadeInUp>
      </SectionContainer>

      {/* ── Feature comparison table ───────────────────────────────────────── */}
      <SectionContainer className="border-t border-border pt-16">
        <FadeInUp className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            Compare every plan
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground">
            The same grading engine across every tier — higher plans add seats,
            throughput and team governance.
          </p>
        </FadeInUp>

        <FadeInUp className="mx-auto mt-10 max-w-5xl overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="py-4 pr-4 text-left font-medium text-foreground">
                  <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                    Capability
                  </span>
                </th>
                {PLANS.map((p) => (
                  <th key={p.code} scope="col" className="px-3 py-4 text-center align-bottom">
                    <span className="block text-sm font-medium text-foreground">{p.name}</span>
                    <span className="mt-0.5 block font-mono text-[11px] tabular text-muted-foreground">
                      {formatPrice(p.priceInr)}
                      {p.priceInr !== null && p.priceInr !== 0 ? "/mo" : ""}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARE.map((section) => (
                <Fragment key={section.group}>
                  <tr className="bg-surface-1">
                    <th
                      scope="colgroup"
                      colSpan={PLANS.length + 1}
                      className="border-b border-border px-0 py-2 text-left"
                    >
                      <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                        {section.group}
                      </span>
                    </th>
                  </tr>
                  {section.rows.map((row) => (
                    <tr key={row.label} className="border-b border-border">
                      <th scope="row" className="py-3 pr-4 text-left font-normal text-foreground">
                        {row.label}
                      </th>
                      {row.values.map((v, i) => (
                        <td key={i} className="px-3 py-3 text-center">
                          {typeof v === "boolean" ? (
                            <Check ok={v} />
                          ) : (
                            <span className="font-mono text-[13px] tabular text-foreground">{v}</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </FadeInUp>
      </SectionContainer>

      {/* ── Pricing FAQ ────────────────────────────────────────────────────── */}
      <SectionContainer className="border-t border-border pt-16">
        <FadeInUp className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            Pricing FAQ
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground">
            Honest answers, straight from how the product actually works.
          </p>
        </FadeInUp>

        <FadeInUp className="mx-auto mt-10 max-w-3xl">
          <Accordion type="single" collapsible className="rounded-xl border border-border bg-card px-5">
            {FAQ.map((item) => (
              <AccordionItem key={item.q} value={item.q} className="border-border">
                <AccordionTrigger className="text-base font-medium text-foreground hover:no-underline">
                  {item.q}
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                  {item.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </FadeInUp>
      </SectionContainer>

      {/* ── CTA band ───────────────────────────────────────────────────────── */}
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
              Start free — pay only when you scale.
            </RevealItem>
            <RevealItem as="p" className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              Create your first test on the Free plan and grade your next exam in
              minutes. Upgrade for more seats, throughput and team governance.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/contact">Contact sales</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
