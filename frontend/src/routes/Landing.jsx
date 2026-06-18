import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { motion, useReducedMotion } from "framer-motion"
import {
  FileText, Shuffle, ScanLine, ShieldCheck, TrendingUp, BuildingIcon,
  Sparkles, Check, ArrowRight, Layers, QrCode,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import BubbleSheet from "./landing/BubbleSheet"
import FlowShowcase from "./landing/FlowShowcase"
import { Reveal, Stagger, staggerItem, CountUp, EASE } from "./landing/Primitives"

// ── Logo mark ─────────────────────────────────────────────────────────────────
function LogoMark({ className = "" }) {
  return (
    <span className={["flex size-7 items-center justify-center rounded-lg bg-primary", className].join(" ")}>
      <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
        {[6, 12, 18].map((cy) => (
          <circle key={cy} cx="8" cy={cy} r="2.4" fill="none" stroke="var(--primary-foreground)" strokeWidth="1.6" />
        ))}
        <circle cx="16" cy="12" r="2.4" fill="var(--primary-foreground)" />
      </svg>
    </span>
  )
}

// ── Sticky nav ────────────────────────────────────────────────────────────────
function LandingNav() {
  const [solid, setSolid] = useState(false)
  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 8)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])
  return (
    <header
      className={[
        "fixed inset-x-0 top-0 z-50 transition-colors duration-300",
        solid ? "border-b border-border bg-background/80 backdrop-blur" : "bg-transparent",
      ].join(" ")}
    >
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-base font-bold">
          <LogoMark /> OMRFlow
        </Link>
        <nav className="ml-auto hidden items-center gap-7 text-sm sm:flex">
          <a href="#how-it-works" className="text-muted-foreground transition-colors hover:text-foreground">How it works</a>
          <a href="#features" className="text-muted-foreground transition-colors hover:text-foreground">Features</a>
          <Link to="/login" className="text-muted-foreground transition-colors hover:text-foreground">Sign in</Link>
        </nav>
        <Button asChild size="sm" className="ml-auto min-h-[40px] sm:ml-0">
          <Link to="/register">Get started</Link>
        </Button>
      </div>
    </header>
  )
}

// ── Hero visual: a live, scanning sheet with floating chips ───────────────────
function FloatingChip({ icon: Icon, text, className, delay = 0 }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={["absolute flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium shadow-lg", className].join(" ")}
      initial={reduce ? false : { opacity: 0, scale: 0.8 }}
      animate={reduce ? {} : { opacity: 1, scale: 1, y: [0, -7, 0] }}
      transition={{
        opacity: { duration: 0.5, delay },
        scale: { duration: 0.5, delay },
        y: { duration: 4, repeat: Infinity, ease: "easeInOut", delay },
      }}
    >
      <Icon className="size-3.5 text-primary" />
      {text}
    </motion.div>
  )
}

function HeroVisual() {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className="relative mx-auto w-full max-w-[300px] sm:max-w-sm"
      initial={reduce ? false : { opacity: 0, y: 30, rotate: -2 }}
      animate={{ opacity: 1, y: 0, rotate: 0 }}
      transition={{ duration: 0.8, ease: EASE, delay: 0.15 }}
    >
      <div className="rotate-[-4deg] rounded-3xl border border-border bg-card p-3 shadow-2xl">
        <BubbleSheet name="Asha Devi" roll="101" scanning className="aspect-[200/264]" />
      </div>
      <FloatingChip icon={Shuffle} text="Per-student shuffle" className="-left-3 top-12 sm:-left-6" delay={0.5} />
      <FloatingChip icon={Check} text="Auto-graded" className="-right-2 top-1/3 sm:-right-6" delay={0.8} />
      <FloatingChip icon={QrCode} text="QR-identified test" className="bottom-10 left-2 sm:left-0" delay={1.1} />
    </motion.div>
  )
}

// ── Stats strip ───────────────────────────────────────────────────────────────
const STATS = [
  { to: 50, suffix: "+", label: "questions per test" },
  { to: 100, suffix: "%", label: "graded server-side" },
  { to: 6, suffix: "", label: "OMR modes & varieties" },
  { to: 0, suffix: "", label: "sheets guessed", note: "never" },
]

// ── Features ──────────────────────────────────────────────────────────────────
const FEATURES = [
  { icon: FileText, title: "Personalised sheets in one PDF", body: "Batch-generate print-ready sheets with a roll grid, QR code and fiducials — pre-print known names or just pick a count." },
  { icon: Shuffle, title: "Per-student shuffle", body: "Shuffle question and option order uniquely per student; each sheet stores its own answer key so grading stays exact." },
  { icon: ScanLine, title: "Scan & auto-grade", body: "Point a camera or feed a stack — sheets are detected, multi-page sheets auto-stitch by QR, grading runs with live progress." },
  { icon: ShieldCheck, title: "Nothing mis-graded silently", body: "Double-marked, faint or smudged bubbles and missing pages go to a review queue instead of being guessed. Set your own rules." },
  { icon: TrendingUp, title: "Analytics & improvement", body: "Score distributions, toppers, hardest questions, percentiles — and test-to-retest deltas per student or class." },
  { icon: BuildingIcon, title: "Folders, sharing & org admin", body: "Organise classes in folders, share to teammates with view/edit, and give admins full oversight — with strict data isolation." },
]

export default function Landing() {
  return (
    <div className="overflow-x-hidden">
      <LandingNav />

      {/* Hero */}
      <section className="px-4 pb-16 pt-28 sm:pt-36">
        <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
          <div>
            <Reveal as="div">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="size-3.5 text-primary" />
                Generate · Scan · Auto-grade · Analyse
              </span>
              <h1 className="mt-5 text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
                Grade a stack of bubble sheets in minutes, not hours
              </h1>
              <p className="mt-5 max-w-xl text-lg text-muted-foreground">
                Turn one class list and one set of questions into a unique, shuffled OMR
                sheet for every student. Scan from any phone, auto-grade the whole stack,
                and turn each test into a full analytics profile.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button asChild size="lg" className="min-h-[44px] gap-1.5">
                  <Link to="/register">Start free <ArrowRight className="size-4" /></Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="min-h-[44px]">
                  <Link to="/login">Sign in</Link>
                </Button>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                No card required · Works with any phone or scanner · Built for tutors, coaching centres & schools
              </p>
            </Reveal>
          </div>
          <HeroVisual />
        </div>
      </section>

      {/* Stats strip */}
      <section className="border-y border-border bg-muted/40">
        <Stagger className="mx-auto grid max-w-5xl grid-cols-2 gap-px px-4 py-10 sm:grid-cols-4" gap={0.08}>
          {STATS.map((s) => (
            <motion.div key={s.label} variants={staggerItem} className="text-center">
              <p className="text-3xl font-bold tabular-nums sm:text-4xl">
                {s.note ? s.note : <CountUp to={s.to} suffix={s.suffix} />}
              </p>
              <p className="mt-1 text-xs text-muted-foreground sm:text-sm">{s.label}</p>
            </motion.div>
          ))}
        </Stagger>
      </section>

      {/* The flow (centerpiece) */}
      <FlowShowcase />

      {/* Features */}
      <section id="features" className="bg-muted/40 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-4">
          <Reveal className="mx-auto max-w-2xl text-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">Why OMRFlow</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to grade faster — and fairer
            </h2>
          </Reveal>
          <Stagger className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" gap={0.07}>
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <motion.div
                key={title}
                variants={staggerItem}
                whileHover={{ y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="rounded-2xl border border-border bg-card p-5 shadow-sm"
              >
                <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="size-5" />
                </span>
                <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{body}</p>
              </motion.div>
            ))}
          </Stagger>
        </div>
      </section>

      {/* CTA band — flat solid brand colour */}
      <section className="bg-primary text-primary-foreground">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center">
          <Reveal>
            <Layers className="mx-auto size-9 opacity-90" />
            <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
              Stop grading by hand
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-primary-foreground/80">
              Create your first test free and grade your next exam in minutes — shuffled
              sheets, auto-grading and analytics included.
            </p>
            <Button asChild size="lg" variant="secondary" className="mt-8 min-h-[44px] gap-1.5">
              <Link to="/register">Start free <ArrowRight className="size-4" /></Link>
            </Button>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-8 sm:flex-row">
          <Link to="/" className="flex items-center gap-2 text-sm font-semibold">
            <LogoMark /> OMRFlow
          </Link>
          <p className="text-xs text-muted-foreground">Auditable, server-side grading · Per-organisation data isolation</p>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/login" className="text-muted-foreground hover:text-foreground">Sign in</Link>
            <Link to="/register" className="font-medium text-primary hover:underline">Create account</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
