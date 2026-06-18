import { Link } from "react-router-dom"
import { motion, useReducedMotion } from "framer-motion"
import { MagneticButton } from "./Micro"
import MaterialIcon from "./MaterialIcon"
import { ease, dur } from "./motion/tokens"

export default function CTA() {
  const reduce = useReducedMotion()
  return (
    <section className="relative overflow-hidden px-4 py-28 sm:py-36">
      {/* ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: "radial-gradient(50% 60% at 50% 50%, rgba(99,102,241,0.18), transparent 70%)" }}
      />
      {/* masked bubble-grid backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          backgroundImage:
            "radial-gradient(circle, transparent 1.5px, rgba(255,255,255,0.05) 1.5px, rgba(255,255,255,0.05) 2.5px, transparent 2.5px)",
          backgroundSize: "26px 26px",
          WebkitMaskImage: "radial-gradient(ellipse 50% 60% at 50% 50%, #000 30%, transparent)",
          maskImage: "radial-gradient(ellipse 50% 60% at 50% 50%, #000 30%, transparent)",
        }}
      />

      <motion.div
        initial={reduce ? false : { opacity: 0, scale: 0.96 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: false, amount: 0.4 }}
        transition={{ duration: dur.hero, ease: ease.outSoft }}
        className="mx-auto max-w-3xl text-center"
      >
        <span className="glass mx-auto flex size-14 items-center justify-center rounded-2xl">
          <MaterialIcon name="layers" className="size-7 text-indigo-300" />
        </span>
        <h2 className="text-display-sm mx-auto mt-6 text-balance text-4xl font-semibold text-white sm:text-[3.25rem]">
          Stop grading <span className="font-serif-accent text-[1.1em] text-cyan-200">by hand</span>.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-balance text-lg leading-relaxed text-neutral-300">
          Create your first test free and grade your next exam in minutes — shuffled sheets,
          auto-grading and analytics included.
        </p>
        <div className="mt-9 flex justify-center">
          <MagneticButton className="p-2">
            {/* conic border beam wrapping the CTA */}
            <span className="landing-beam relative inline-flex rounded-2xl p-[1.5px]">
              <Link
                to="/register"
                className="group relative z-10 inline-flex min-h-[52px] items-center gap-2 rounded-2xl bg-white px-8 text-base font-semibold text-neutral-950 transition-colors hover:bg-neutral-100"
              >
                Start free
                <MaterialIcon name="arrow" className="size-4 transition-transform duration-200 group-hover:translate-x-0.5" />
              </Link>
            </span>
          </MagneticButton>
        </div>
        <p className="mt-4 font-mono-data text-xs text-neutral-500">No card required · Cancel anytime</p>
      </motion.div>
    </section>
  )
}
