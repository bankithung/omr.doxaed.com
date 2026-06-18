import { Link } from "react-router-dom"
import { motion, useReducedMotion } from "framer-motion"
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

const container = { hidden: {}, show: { transition: { staggerChildren: stagger.tight } } }
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: dur.enter, ease: ease.out } },
}

export default function Footer() {
  const reduce = useReducedMotion()
  return (
    <footer className="border-t border-white/10 px-4 py-12">
      <motion.div
        variants={reduce ? undefined : container}
        initial={reduce ? false : "hidden"}
        whileInView="show"
        viewport={{ once: false, amount: 0.3 }}
        className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row"
      >
        <motion.div variants={reduce ? undefined : item}>
          <Link to="/" className="flex items-center gap-2 text-sm font-semibold text-white">
            <LogoMark /> OMRFlow
          </Link>
        </motion.div>
        <motion.p variants={reduce ? undefined : item} className="text-center text-xs text-neutral-500">
          Auditable, server-side grading · Per-organisation data isolation
        </motion.p>
        <motion.div variants={reduce ? undefined : item} className="flex items-center gap-4 text-sm">
          <Link to="/login" className="text-neutral-300 transition-colors hover:text-white">Sign in</Link>
          <Link to="/register" className="font-medium text-cyan-300 transition-colors hover:text-cyan-200">Create account</Link>
        </motion.div>
      </motion.div>
    </footer>
  )
}
