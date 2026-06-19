import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * Security — an honest trust + data-safety page. Every claim here describes how
 * the product is ACTUALLY built (server-side grading against a stored key, the
 * review queue, encrypted PII, owner-scoped multi-tenancy, audit logging, JWT +
 * django-axes, env-only secrets). It deliberately makes NO compliance claims
 * (no SOC 2 / ISO / GDPR certification, no third-party audit, no uptime SLA) and
 * is explicit that production hardening — TLS, backups, monitoring, external
 * audit — is the operator's deployment responsibility, not a fabricated promise.
 */

// ── Section cards — real, product-level safeguards only ───────────────────────
const SAFEGUARDS = [
  {
    icon: "shield",
    title: "Server-side grading",
    body: "Every answer sheet is graded on the server against that sheet's own stored answer key — never in the browser. Scores can't be computed or tampered with on the client, so a published result always traces back to the key the test was generated with.",
  },
  {
    icon: "task",
    title: "Never guessed — review queue",
    body: "Faint, double-marked or ambiguous bubbles aren't guessed. Low-confidence reads are routed to a review queue with the cropped bubble image so a human makes the call. A grade is either confidently read or explicitly reviewed.",
  },
  {
    icon: "lock",
    title: "Encrypted student PII",
    body: "Student names and roll numbers are encrypted at rest. Only the fields a public result actually needs are ever exposed on the result portal — the rest of a student's data stays scoped to its owner.",
  },
  {
    icon: "folder",
    title: "Owner-scoped multi-tenancy",
    body: "Every test, sheet, roster and result belongs to exactly one owner — a user XOR an organisation. Access is role-checked on every request, so one tenant's data is never reachable from another's session.",
  },
  {
    icon: "checklist",
    title: "Audit-logged admin actions",
    body: "Sensitive admin and grading actions are written to an audit log within the organisation, so changes can be traced after the fact and a disputed result can be explained.",
  },
  {
    icon: "devices",
    title: "Authentication & lockout",
    body: "Access uses JWT authentication, and repeated failed sign-ins are throttled and locked out with django-axes to blunt brute-force and credential-stuffing attempts.",
  },
]

// ── How a grade is protected, end to end — honest pipeline, no embellishment ──
const PIPELINE = [
  {
    title: "Keyed at generation",
    body: "Each generated sheet carries its own answer key. Grading reads that stored key — it is never inferred from other students' sheets.",
  },
  {
    title: "Aligned, then read",
    body: "A scan is aligned using the sheet's QR identity and fiducial markers, so bubbles are read from the correct positions regardless of the phone or scanner used.",
  },
  {
    title: "Confident or reviewed",
    body: "High-confidence reads are graded automatically; anything uncertain goes to the review queue with its cropped image — nothing is silently assumed.",
  },
  {
    title: "Recorded & owner-scoped",
    body: "The result is stored against its owner, encrypted where it holds PII, and surfaced publicly only with the minimal fields a result portal needs.",
  },
]

function SafeguardCard({ item }) {
  return (
    <RevealItem className="flex h-full flex-col rounded-xl border border-border bg-card p-6 transition-colors hover:border-border-strong">
      <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
        <MaterialIcon name={item.icon} className="size-5" />
      </span>
      <h3 className="mt-4 text-base font-medium text-foreground">{item.title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
    </RevealItem>
  )
}

export default function Security() {
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
              Security
            </span>
            <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Built so a grade can be <span className="text-primary">trusted</span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              DoxaEd OMR grades on the server against each sheet's stored key,
              never guesses an uncertain read, and keeps every student record
              owned, encrypted and auditable. Here's exactly how — and what's
              honestly your operator's responsibility to deploy.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Safeguard cards ────────────────────────────────────────────────── */}
      <SectionContainer className="pt-0">
        <Reveal as="div" className="mx-auto grid max-w-6xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SAFEGUARDS.map((item) => (
            <SafeguardCard key={item.title} item={item} />
          ))}
        </Reveal>
      </SectionContainer>

      {/* ── Grade-protection pipeline ──────────────────────────────────────── */}
      <SectionContainer className="border-t border-border pt-16">
        <FadeInUp className="mx-auto max-w-2xl text-center">
          <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            End to end
          </span>
          <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
            How a grade is protected
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground">
            From the moment a sheet is generated to the moment a result is shared,
            every step is keyed, checked and recorded.
          </p>
        </FadeInUp>

        <Reveal as="ol" className="mx-auto mt-12 grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE.map((step, i) => (
            <RevealItem
              as="li"
              key={step.title}
              className="flex h-full flex-col rounded-xl border border-border bg-card p-5"
            >
              <span className="flex size-8 items-center justify-center rounded-lg border border-border bg-surface-2 font-mono text-sm font-medium text-primary">
                {i + 1}
              </span>
              <h3 className="mt-4 text-sm font-medium text-foreground">{step.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </RevealItem>
          ))}
        </Reveal>
      </SectionContainer>

      {/* ── Secrets & data handling ────────────────────────────────────────── */}
      <SectionContainer className="border-t border-border pt-16">
        <div className="mx-auto grid max-w-5xl items-start gap-10 lg:grid-cols-[1fr_1fr] lg:gap-14">
          <FadeInUp>
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Data handling
            </span>
            <h2 className="mt-3 text-2xl font-medium tracking-tight text-foreground sm:text-3xl">
              Only what a result needs, scoped to its owner
            </h2>
            <div className="mt-5 space-y-4 text-base leading-relaxed text-muted-foreground">
              <p>
                You upload only the student data you choose. Names and roll
                numbers are encrypted at rest, and the public result portal
                surfaces just the minimal fields a result needs — never a
                student's full record.
              </p>
              <p>
                Every row is owned by a single user or organisation, and access
                is role-checked on each request. There is no cross-tenant read
                path: one account cannot reach another's tests, sheets or results.
              </p>
              <p>
                Application secrets — keys, database credentials, tokens — are
                read from environment variables only. They are never committed to
                the codebase or hard-coded.
              </p>
            </div>
          </FadeInUp>

          <FadeInUp delay={0.1}>
            <div className="rounded-xl border border-border bg-card p-6">
              <p className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                Operator's responsibility
              </p>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                DoxaEd OMR is honest about its boundary. The application provides
                the safeguards above, but the production posture below depends on
                how an operator deploys it — and we make no certification or
                compliance claim on their behalf.
              </p>
              <ul className="mt-5 space-y-3">
                {[
                  "TLS / HTTPS termination at the deployment edge",
                  "Database backups & restore testing",
                  "Monitoring, logging & alerting in production",
                  "Any third-party security audit or compliance certification",
                ].map((line) => (
                  <li key={line} className="flex items-start gap-2.5 text-sm text-foreground">
                    <MaterialIcon name="arrow" className="mt-0.5 size-3.5 shrink-0 text-primary" />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-5 font-mono text-[11px] leading-relaxed text-muted-foreground">
                We don't claim audits or certifications we don't have.
              </p>
            </div>
          </FadeInUp>
        </div>
      </SectionContainer>

      {/* ── Responsible disclosure ─────────────────────────────────────────── */}
      <SectionContainer className="border-t border-border pt-16">
        <FadeInUp className="mx-auto max-w-3xl">
          <div className="rounded-xl border border-border bg-card p-6 sm:p-8">
            <div className="flex items-start gap-4">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-primary">
                <MaterialIcon name="shield" className="size-5" />
              </span>
              <div className="min-w-0">
                <h2 className="text-xl font-medium tracking-tight text-foreground sm:text-2xl">
                  Responsible disclosure
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  If you believe you've found a security vulnerability, please
                  report it privately so we can investigate and fix it before it's
                  disclosed publicly. Include steps to reproduce and any affected
                  URLs. Please don't access, modify or exfiltrate data that isn't
                  yours while testing.
                </p>
                <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Button asChild className="h-10 px-5 text-sm">
                    <a href="mailto:doxaed@gmail.com?subject=Security%20disclosure">
                      <MaterialIcon name="arrow" className="size-4" />
                      Email doxaed@gmail.com
                    </a>
                  </Button>
                  <p className="font-mono text-[11px] text-muted-foreground">
                    We'll acknowledge reports we can reproduce.
                  </p>
                </div>
              </div>
            </div>
          </div>
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
              Grade with confidence
            </RevealItem>
            <RevealItem as="p" className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              Try the full grading engine free — server-side, never guessed, and
              owned by you from the first sheet.
            </RevealItem>
            <RevealItem className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Button size="lg" asChild className="h-11 px-6 text-sm">
                <Link to="/register">Start free</Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="h-11 px-6 text-sm">
                <Link to="/contact">Contact us</Link>
              </Button>
            </RevealItem>
          </Reveal>
        </SectionContainer>
      </section>
    </PublicLayout>
  )
}
