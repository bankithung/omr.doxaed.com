import { Link } from "react-router-dom"
import { motion, useScroll, useSpring, useTransform } from "framer-motion"
import { ArrowRight } from "lucide-react"
import { MagneticButton } from "./Micro"
import { palette } from "./motion/tokens"

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

// Fixed top scroll-progress rail (the spine of the 4-act narrative).
export function ScrollRail() {
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 90, damping: 30, restDelta: 0.001, mass: 0.4 })
  return (
    <motion.div
      aria-hidden
      style={{ scaleX, transformOrigin: "left" }}
      className="fixed inset-x-0 top-0 z-[60] h-0.5 bg-gradient-to-r from-indigo-500 via-cyan-400 to-teal-400"
    />
  )
}

export default function LandingNav() {
  const { scrollY } = useScroll()
  const bg = useTransform(scrollY, [0, 80], ["rgba(5,6,10,0)", "rgba(8,10,18,0.72)"])
  const borderColor = useTransform(scrollY, [0, 80], ["rgba(255,255,255,0)", palette.border])
  const blur = useTransform(scrollY, [0, 80], ["blur(0px)", "blur(12px)"])

  return (
    <motion.header
      style={{ backgroundColor: bg, borderBottomColor: borderColor, backdropFilter: blur, WebkitBackdropFilter: blur }}
      className="fixed inset-x-0 top-0 z-50 border-b border-transparent"
    >
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-base font-bold text-white">
          <LogoMark /> OMRFlow
        </Link>
        <nav className="ml-auto hidden items-center gap-7 text-sm sm:flex">
          <a href="#how-it-works" className="text-neutral-300 transition-colors hover:text-white">How it works</a>
          <a href="#features" className="text-neutral-300 transition-colors hover:text-white">Features</a>
          <Link to="/login" className="text-neutral-300 transition-colors hover:text-white">Sign in</Link>
        </nav>
        <MagneticButton className="ml-auto p-1.5 sm:ml-0" strength={0.25} labelStrength={0.45}>
          <Link
            to="/register"
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-white px-4 text-sm font-semibold text-neutral-950 shadow-[0_0_30px_-6px_rgba(99,102,241,0.7)] transition-colors hover:bg-neutral-100"
          >
            Get started <ArrowRight className="size-4" />
          </Link>
        </MagneticButton>
      </div>
    </motion.header>
  )
}
