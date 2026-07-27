import { useState } from "react"
import { Link } from "react-router-dom"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import PublicLayout from "@/components/PublicLayout"
import SectionContainer from "@/routes/landing/SectionContainer"
import MaterialIcon from "@/routes/landing/MaterialIcon"
import { Reveal, RevealItem, FadeInUp } from "@/routes/landing/motion/reveal"

/**
 * Contact — an honest contact section. There is NO contact backend, so the form
 * does NOT fake a submission/success: on submit it composes a real prefilled
 * `mailto:doxaed@gmail.com` and hands off to the user's mail client. A copy
 * button puts the address on the clipboard. Real channels only (hello@ /
 * support@ / doxaed.com). No fabricated phone numbers, addresses or SLAs.
 */

const CHANNELS = [
  {
    icon: "task",
    label: "Email us",
    value: "doxaed@gmail.com",
    href: "mailto:doxaed@gmail.com",
    copy: "doxaed@gmail.com",
  },
  {
    icon: "devices",
    label: "On the web",
    value: "doxaed.com",
    href: "https://doxaed.com",
    external: true,
  },
]

function CopyButton({ value, label }) {
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value)
      toast.success(`Copied ${value}`)
    } catch {
      toast.error("Couldn't copy, please select and copy manually")
    }
  }
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={handleCopy}
      className="h-9 px-2 text-muted-foreground hover:text-foreground"
      aria-label={`Copy ${label}`}
    >
      <MaterialIcon name="checklist" className="size-4" />
      <span className="text-xs">Copy</span>
    </Button>
  )
}

function ContactForm() {
  const [form, setForm] = useState({ name: "", email: "", message: "" })

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  // Compose a real mailto: with the message prefilled. No backend, no fake
  // "message sent" — we hand off to the user's email client honestly.
  function handleSubmit(e) {
    e.preventDefault()
    const subject = encodeURIComponent(
      form.name ? `DoxaEd OMR enquiry from ${form.name}` : "DoxaEd OMR enquiry"
    )
    const bodyLines = [
      form.message,
      "",
      "n/a",
      form.name ? `Name: ${form.name}` : null,
      form.email ? `Email: ${form.email}` : null,
    ].filter(Boolean)
    const body = encodeURIComponent(bodyLines.join("\n"))
    window.location.href = `mailto:doxaed@gmail.com?subject=${subject}&body=${body}`
    toast.message("Opening your email app", {
      description: "We've prefilled a message to doxaed@gmail.com.",
    })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-border bg-card p-6 sm:p-8"
      noValidate
    >
      <div className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="contact-name">Name</Label>
          <Input
            id="contact-name"
            name="name"
            value={form.name}
            onChange={update("name")}
            placeholder="Your name"
            autoComplete="name"
            className="h-10"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="contact-email">Email</Label>
          <Input
            id="contact-email"
            name="email"
            type="email"
            value={form.email}
            onChange={update("email")}
            placeholder="you@example.com"
            autoComplete="email"
            className="h-10"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="contact-message">Message</Label>
          <Textarea
            id="contact-message"
            name="message"
            value={form.message}
            onChange={update("message")}
            placeholder="Tell us about your tests, batch sizes, or what you'd like to know."
            rows={5}
            className="min-h-[120px]"
          />
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button type="submit" className="h-10 px-5 text-sm">
          <MaterialIcon name="arrow" className="size-4" />
          Compose email
        </Button>
        <p className="font-mono text-[11px] text-muted-foreground">
          Opens your email app, nothing is sent automatically.
        </p>
      </div>
    </form>
  )
}

export default function Contact() {
  return (
    <PublicLayout>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[380px]"
          style={{
            background:
              "radial-gradient(55% 50% at 50% 0%, color-mix(in oklch, var(--color-primary) 12%, transparent), transparent 72%)",
          }}
        />
        <SectionContainer className="pt-14 pb-8 sm:pt-16 text-center">
 <FadeInUp className="mx-auto ">
            <span className="block font-mono text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Contact
            </span>
 <h1 className="mx-auto mt-3 text-4xl font-medium tracking-tight text-foreground sm:text-5xl">
              Let's <span className="text-indigo">talk</span>
            </h1>
 <p className="mx-auto mt-5 text-base text-muted-foreground sm:text-lg">
              Questions about plans, a demo for your coaching centre, or help
              getting set up? Send us a note, we read every message.
            </p>
          </FadeInUp>
        </SectionContainer>
      </section>

      {/* ── Form + channels ────────────────────────────────────────────────── */}
      <SectionContainer className="pt-0">
 <div className="mx-auto grid items-start gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:gap-12">
          <FadeInUp>
            <ContactForm />
          </FadeInUp>

          <FadeInUp delay={0.1}>
            <Reveal as="div" className="space-y-4">
              <RevealItem>
                <h2 className="text-base font-medium text-foreground">Other ways to reach us</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Prefer email? Use the right inbox and we'll get back to you.
                </p>
              </RevealItem>

              {CHANNELS.map((c) => (
                <RevealItem
                  key={c.value}
                  className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:border-border-strong"
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-indigo">
                    <MaterialIcon name={c.icon} className="size-[18px]" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                      {c.label}
                    </p>
                    <a
                      href={c.href}
                      {...(c.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                      className="block truncate text-sm font-medium text-foreground transition-colors hover:text-indigo"
                    >
                      {c.value}
                    </a>
                  </div>
                  {c.copy && <CopyButton value={c.copy} label={c.label} />}
                </RevealItem>
              ))}

              <RevealItem className="rounded-xl border border-border bg-surface-1 p-4">
                <p className="text-sm text-muted-foreground">
                  Already have an account?{" "}
                  <Link to="/login" className="font-medium text-indigo underline-offset-4 hover:underline">
                    Sign in
                  </Link>{" "}
                  or{" "}
                  <Link to="/register" className="font-medium text-indigo underline-offset-4 hover:underline">
                    start free
                  </Link>
                  .
                </p>
              </RevealItem>
            </Reveal>
          </FadeInUp>
        </div>
      </SectionContainer>
    </PublicLayout>
  )
}
