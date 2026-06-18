import { Link } from "react-router-dom"
import { motion, useReducedMotion } from "framer-motion"
import { MagneticButton } from "./Micro"
import MaterialIcon from "./MaterialIcon"
import { ease, dur, stagger } from "./motion/tokens"

function LogoMark() {
  return (
    <span className="flex size-7 items-center justify-center rounded-lg bg-indigo-500">
      <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
        {[6, 12, 18].map((cy) => (
          <circle key={cy} cx="8" cy={cy} r="2.4" fill="none" stroke="#fff" strokeWidth="1.6" />
        ))}
        <circle cx="16" cy="12" r="2.4" fill="#fff" />
      </svg>
    </span>
  )
}

// ── Real content only — no invented pages, no fake social, no fake newsletter ──
// Product nav: real in-page anchors + real app routes.
const PRODUCT_LINKS = [
  { label: "How it works", to: "#how-it-works", anchor: true },
  { label: "Features", to: "#features", anchor: true },
  { label: "Sign in", to: "/login" },
  { label: "Create account", to: "/register" },
]

// Real product OMR modes (rendered as #features anchors — not broken links).
const OMR_MODES = [
  "Standard MCQ",
  "Roster pre-bubbled roll (auto-identify)",
  "Competitive / sectional (NEET · UPSC style)",
  "Per-student shuffle",
  "4 or 5 options",
]

// Real product capabilities (anchors to #features).
const CAPABILITIES = [
  "Batch sheet generation",
  "Shuffled question papers",
  "Scan & auto-grade",
  "Inline scan correction",
  "Review queue (never guessed)",
  "Configurable multi-mark rules",
  "Analytics & item analysis",
  "Two-page report cards",
  "Public result portal",
  "Folders & sharing",
  "Organisations & roles",
]

// Trust points (real).
const TRUST_POINTS = [
  "Server-side grading",
  "Auditable results",
  "Encrypted student PII",
  "Per-organisation data isolation",
  "Works with any phone or scanner",
]

const container = { hidden: {}, show: { transition: { staggerChildren: stagger.tight } } }
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: dur.enter, ease: ease.out } },
}

function ColHeading({ children }) {
  return (
    <p className="font-mono-data text-[11px] font-medium uppercase tracking-[0.16em] text-neutral-500">{children}</p>
  )
}

// Plain capability/mode entry — anchors to #features (a real destination).
function FeatureItem({ children }) {
  return (
    <li>
      <a href="#features" className="text-sm text-neutral-400 transition-colors hover:text-white">
        {children}
      </a>
    </li>
  )
}

function FooterLink({ to, anchor, children }) {
  const cls = "text-sm text-neutral-400 transition-colors hover:text-white"
  return anchor ? <a href={to} className={cls}>{children}</a> : <Link to={to} className={cls}>{children}</Link>
}

export default function Footer() {
  const reduce = useReducedMotion()
  return (
    <footer className="border-t border-white/10 px-4 pb-10 pt-16 sm:px-6 sm:pt-20">
      <motion.div
        variants={reduce ? undefined : container}
        initial={reduce ? false : "hidden"}
        whileInView="show"
        viewport={{ once: false, amount: 0.15 }}
        className="mx-auto max-w-6xl"
      >
        {/* top: brand + sitemap columns, hairline-divided */}
        <div className="grid gap-x-8 gap-y-10 lg:grid-cols-[1.6fr_1fr_1.3fr_1.3fr_1fr_1fr]">
          {/* brand block */}
          <motion.div variants={reduce ? undefined : item} className="max-w-sm lg:pr-6">
            <Link to="/" className="flex items-center gap-2 text-white" aria-label="DoxaEd OMR — home">
              <LogoMark />
              <span className="flex items-baseline gap-1.5">
                <span className="text-[1.05rem] font-semibold tracking-tight">DoxaEd</span>
                <span className="font-mono-data text-[11px] font-medium uppercase tracking-[0.28em] text-cyan-300">OMR</span>
              </span>
            </Link>
            <p className="mt-4 text-sm leading-relaxed text-neutral-400">
              Shuffled OMR sheets, scanned and auto-graded — every test a full{" "}
              <span className="font-serif-accent text-base text-cyan-200">analytics</span> profile.
            </p>
            <MagneticButton className="mt-5 p-1.5" strength={0.2} labelStrength={0.4}>
              <Link
                to="/register"
                className="group inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-neutral-950 shadow-[0_0_36px_-10px_rgba(99,102,241,0.8)] transition-colors hover:bg-neutral-100"
              >
                Start free
                <MaterialIcon name="arrow" className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
              </Link>
            </MagneticButton>
            <p className="mt-5 font-mono-data text-[11px] text-neutral-600">DoxaEd OMR · omr.doxaed.com</p>
          </motion.div>

          {/* product column */}
          <motion.nav variants={reduce ? undefined : item} aria-label="Product" className="lg:border-l lg:border-white/5 lg:pl-6">
            <ColHeading>Product</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {PRODUCT_LINKS.map((l) => (
                <li key={l.label}>
                  <FooterLink to={l.to} anchor={l.anchor}>{l.label}</FooterLink>
                </li>
              ))}
            </ul>
          </motion.nav>

          {/* OMR modes column */}
          <motion.div variants={reduce ? undefined : item} className="lg:border-l lg:border-white/5 lg:pl-6">
            <ColHeading>OMR modes</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {OMR_MODES.map((m) => (
                <FeatureItem key={m}>{m}</FeatureItem>
              ))}
            </ul>
          </motion.div>

          {/* capabilities column */}
          <motion.div variants={reduce ? undefined : item} className="lg:border-l lg:border-white/5 lg:pl-6">
            <ColHeading>Capabilities</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {CAPABILITIES.map((c) => (
                <FeatureItem key={c}>{c}</FeatureItem>
              ))}
            </ul>
          </motion.div>

          {/* trust column */}
          <motion.div variants={reduce ? undefined : item} className="lg:border-l lg:border-white/5 lg:pl-6">
            <ColHeading>Why DoxaEd OMR</ColHeading>
            <ul className="mt-4 space-y-2.5">
              {TRUST_POINTS.map((t) => (
                <li key={t} className="flex items-start gap-2 text-sm text-neutral-400">
                  <MaterialIcon name="task" className="mt-0.5 size-3.5 shrink-0 text-emerald-400/80" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* contact column — real mailto + real site only */}
          <motion.div variants={reduce ? undefined : item} className="lg:border-l lg:border-white/5 lg:pl-6">
            <ColHeading>Get in touch</ColHeading>
            <ul className="mt-4 space-y-2.5">
              <li>
                <a href="mailto:hello@doxaed.com" className="flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-white">
                  <MaterialIcon name="task" className="size-3.5 shrink-0 text-cyan-300" />
                  hello@doxaed.com
                </a>
              </li>
              <li>
                <a href="mailto:support@doxaed.com" className="flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-white">
                  <MaterialIcon name="task" className="size-3.5 shrink-0 text-cyan-300" />
                  support@doxaed.com
                </a>
              </li>
              <li>
                <a href="https://doxaed.com" rel="noreferrer" className="flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-white">
                  <MaterialIcon name="devices" className="size-3.5 shrink-0 text-cyan-300" />
                  doxaed.com
                </a>
              </li>
            </ul>
          </motion.div>
        </div>

        {/* bottom bar */}
        <motion.div
          variants={reduce ? undefined : item}
          className="mt-14 flex flex-col items-center justify-between gap-3 border-t border-white/10 pt-6 sm:flex-row"
        >
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
            <p className="font-mono-data text-xs text-neutral-500">© 2026 DoxaEd OMR</p>
            <Link to="/terms" className="text-xs text-neutral-400 transition-colors hover:text-white">
              Terms
            </Link>
            <Link to="/privacy" className="text-xs text-neutral-400 transition-colors hover:text-white">
              Privacy
            </Link>
          </div>
          <p className="text-center text-xs text-neutral-500">
            Built for tutors, coaching centres, schools &amp; competitive-exam prep
          </p>
          <a href="#top" className="group flex items-center gap-1.5 text-xs text-neutral-400 transition-colors hover:text-white">
            Back to top
            <MaterialIcon name="arrow" className="size-3.5 -rotate-90 transition-transform duration-200 group-hover:-translate-y-0.5" />
          </a>
        </motion.div>
      </motion.div>
    </footer>
  )
}
