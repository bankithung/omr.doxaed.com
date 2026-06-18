import { Link } from "react-router-dom"
import {
  FileText,
  Shuffle,
  ScanLine,
  ShieldCheck,
  TrendingUp,
  BuildingIcon,
} from "lucide-react"
import { Button } from "@/components/ui/button"

const FEATURES = [
  {
    icon: FileText,
    title: "Personalized OMR sheets in one PDF",
    body: "Batch-generate print-ready sheets with a roll-number grid, QR code, and fiducial markers — pre-print known student names or just pick a count.",
  },
  {
    icon: Shuffle,
    title: "Per-student shuffle to deter copying",
    body: "Optionally shuffle question and option order uniquely per student; each sheet stores its own answer key so grading stays exact.",
  },
  {
    icon: ScanLine,
    title: "Scan and auto-grade, no manual capture",
    body: "Point the camera or feed a stack — sheets are detected automatically, multi-page sheets auto-stitch by QR, and grading runs async with live progress.",
  },
  {
    icon: ShieldCheck,
    title: "Nothing is silently mis-graded",
    body: "Double-marked, faint, or smudged bubbles and missing pages go to a review queue instead of being guessed — every result is auditable.",
  },
  {
    icon: TrendingUp,
    title: "Analytics and improvement tracking",
    body: "See score distributions, toppers, and hardest questions, then compare a student or class across test-to-retest series to show real deltas.",
  },
  {
    icon: BuildingIcon,
    title: "Organizations with admin oversight",
    body: "Invite teachers into a shared workspace, see all members' tests and scans, and manage seats and billing — with strict org-level data isolation.",
  },
]

const STEPS = [
  {
    title: "Build the test",
    body: "Add MCQs and mark the correct options.",
  },
  {
    title: "Generate sheets",
    body: "Create personalized OMR PDFs for your roster.",
  },
  {
    title: "Scan",
    body: "Upload photos or scans from any device.",
  },
  {
    title: "Analyze",
    body: "Get instant scores, review flags, and analytics.",
  },
]

export default function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-4xl px-4 text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Grade a stack of bubble sheets in seconds, not hours
          </h1>
          <p className="mt-4 text-base text-muted-foreground sm:text-lg">
            Create MCQ tests, generate personalized OMR sheets, and scan them with any
            phone or scanner. OMRFlow auto-grades every sheet, flags anything it can't read
            for sure, and tracks each student's improvement across retests.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link to="/register">Start grading free</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* One-liner proof strip */}
      <section>
        <div className="mx-auto max-w-4xl px-4 pb-4 text-center">
          <p className="text-sm text-muted-foreground">
            Built for tutors, coaching centers, and schools — with strict per-organization
            data isolation and auditable, server-side grading.
          </p>
        </div>
      </section>

      {/* Feature grid */}
      <section>
        <div className="mx-auto max-w-6xl px-4 py-12">
          <p className="text-center text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Everything you need to grade faster
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="rounded-xl border bg-card p-4 shadow-sm">
                <Icon className="size-5 text-muted-foreground" />
                <h3 className="mt-3 text-lg font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section>
        <div className="mx-auto max-w-4xl px-4 py-12">
          <h2 className="text-center text-2xl font-bold">
            From test to graded results in four steps
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <div key={step.title} className="rounded-xl border p-4">
                <span className="flex size-7 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {i + 1}
                </span>
                <h3 className="mt-3 text-base font-semibold">{step.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA band */}
      <section className="border-t border-b bg-muted/50">
        <div className="mx-auto max-w-4xl px-4 py-12 text-center">
          <h2 className="text-2xl font-bold">Stop grading by hand</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first test free and grade your next exam in minutes.
          </p>
          <Button asChild size="lg" className="mt-6">
            <Link to="/register">Start grading free</Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 sm:flex-row">
          <span className="text-sm text-muted-foreground">OMRFlow</span>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/login" className="text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
            <Link
              to="/register"
              className="text-primary underline-offset-4 hover:underline"
            >
              Create account
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
