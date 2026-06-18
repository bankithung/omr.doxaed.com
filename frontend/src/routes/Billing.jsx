import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { toast } from "sonner"
import { useOrg } from "@/org/OrgContext"
import { listPlans, getPlan, subscribe } from "@/api/billing"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { CheckIcon, ZapIcon, BuildingIcon, UsersIcon, StarIcon } from "lucide-react"

// Derive a human-readable price label from price_inr string (e.g. "0.00" → "Free", "500.00" → "₹500 / month").
function derivePriceLabel(price_inr) {
  const n = parseFloat(price_inr)
  if (!n) return "Free"
  return `₹${n.toLocaleString("en-IN")} / month`
}

// Derive a limit label: null → "Unlimited", number → "{n} {unit}".
function limitLabel(value, unit) {
  if (value === null || value === undefined) return `Unlimited ${unit}`
  return `${value} ${unit}`
}

// Build the limits list to display in a PlanCard from backend limits object.
function buildLimitLines(limits) {
  return [
    limitLabel(limits.seat_limit, limits.seat_limit === 1 ? "seat" : "seats"),
    limitLabel(limits.students_per_generation_limit, "students / generation"),
    limitLabel(limits.generations_per_day_limit, "generations / day"),
    limitLabel(limits.monthly_scan_limit, "scans / month"),
  ]
}

// Pick a card icon based on plan code.
const PLAN_ICONS = {
  free: UsersIcon,
  team: ZapIcon,
  business: BuildingIcon,
  enterprise: StarIcon,
}

// Plans highlighted as "Popular".
const HIGHLIGHT_CODES = new Set(["team"])

function UsageBar({ label, used, limit }) {
  if (limit === null || limit === undefined) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{label}</span>
          <span className="font-medium">{used ?? 0} / Unlimited</span>
        </div>
      </div>
    )
  }

  const pct = limit > 0 ? Math.min(100, Math.round(((used ?? 0) / limit) * 100)) : 0
  const isWarning = pct >= 80
  const isDanger = pct >= 95

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span
          className={[
            "font-medium",
            isDanger
              ? "text-destructive"
              : isWarning
              ? "text-amber-600 dark:text-amber-400"
              : "text-foreground",
          ].join(" ")}
        >
          {used ?? 0} / {limit}
        </span>
      </div>
      <Progress
        value={pct}
        className={[
          "h-2",
          isDanger
            ? "[&_[data-slot=progress-indicator]]:bg-destructive"
            : isWarning
            ? "[&_[data-slot=progress-indicator]]:bg-amber-500"
            : "",
        ].join(" ")}
      />
    </div>
  )
}

function PlanCard({ plan, currentPlanCode, orgId, onSubscribeSuccess }) {
  const isCurrent = plan.code === currentPlanCode
  const [loading, setLoading] = useState(false)
  const Icon = PLAN_ICONS[plan.code] ?? UsersIcon
  const isHighlight = HIGHLIGHT_CODES.has(plan.code)
  const priceLabel = derivePriceLabel(plan.price_inr)
  const price = parseFloat(plan.price_inr)
  const limitLines = buildLimitLines(plan.limits)

  async function handleSubscribe() {
    setLoading(true)
    try {
      const data = await subscribe(orgId, plan.code)
      if (data?.short_url) {
        window.open(data.short_url, "_blank", "noopener,noreferrer")
        toast.success("Complete payment in the new tab")
      } else {
        toast.success("Subscription updated successfully")
        onSubscribeSuccess?.()
      }
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 403) {
        toast.error(detail || "You need admin access to change the plan")
      } else if (
        detail &&
        (detail.toLowerCase().includes("razorpay") ||
          detail.toLowerCase().includes("api key") ||
          detail.toLowerCase().includes("not configured"))
      ) {
        toast.error("Razorpay isn't configured yet — add your API keys to enable checkout.")
      } else {
        toast.error(
          detail || "Razorpay isn't configured yet — add your API keys to enable checkout."
        )
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className={[
        "relative flex flex-col rounded-2xl border p-6 transition-shadow",
        isHighlight
          ? "border-primary shadow-md shadow-primary/10 ring-1 ring-primary"
          : "border-border",
        isCurrent ? "bg-muted/40" : "bg-background",
      ].join(" ")}
    >
      {isHighlight && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-xs font-semibold text-primary-foreground">
          Popular
        </span>
      )}

      <div className="mb-4 flex items-center gap-2.5">
        <div
          className={[
            "flex size-9 items-center justify-center rounded-lg",
            isHighlight ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
          ].join(" ")}
        >
          <Icon className="size-4" />
        </div>
        <div>
          <h3 className="font-semibold leading-tight">{plan.name}</h3>
        </div>
      </div>

      <div className="mb-5">
        <span className="text-2xl font-bold">{priceLabel}</span>
      </div>

      <ul className="mb-6 space-y-2 text-sm">
        {limitLines.map((label, i) => (
          <li key={i} className="flex items-center gap-2 text-muted-foreground">
            <CheckIcon className="size-3.5 shrink-0 text-primary" />
            {label}
          </li>
        ))}
      </ul>

      <div className="mt-auto">
        {isCurrent ? (
          <div className="flex items-center justify-center rounded-lg border border-border bg-muted py-2 text-sm font-medium text-muted-foreground">
            Current plan
          </div>
        ) : (
          <Button className="w-full" onClick={handleSubscribe} disabled={loading}>
            {loading ? "Processing…" : price ? "Upgrade" : "Downgrade to Free"}
          </Button>
        )}
      </div>
    </div>
  )
}

export default function Billing() {
  const { id: orgId } = useParams()
  const { orgs } = useOrg()
  const [planData, setPlanData] = useState(null)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const org = orgs.find((o) => String(o.id) === String(orgId))

  async function fetchPlan() {
    setLoading(true)
    setError(null)
    try {
      const [orgPlan, allPlans] = await Promise.all([getPlan(orgId), listPlans()])
      setPlanData(orgPlan)
      setPlans(allPlans)
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to load plan information"
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPlan()
  }, [orgId]) // eslint-disable-line react-hooks/exhaustive-deps

  const currentPlanCode = planData?.plan?.code ?? "free"
  const usage = planData?.usage ?? {}
  const limits = planData?.limits ?? {}

  const statusBadgeClass =
    planData?.status === "active"
      ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
      : planData?.status === "trialing"
      ? "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300"
      : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-1 flex items-center gap-2 text-sm text-muted-foreground">
            <Link to={`/organizations/${orgId}/members`} className="hover:text-foreground">
              {org?.name ?? "Organization"}
            </Link>
            <span>/</span>
            <span>Billing</span>
          </div>
          <h1 className="text-2xl font-bold">Billing &amp; Subscription</h1>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="h-32 animate-pulse rounded-2xl bg-muted" />
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="h-64 animate-pulse rounded-2xl bg-muted" />
            <div className="h-64 animate-pulse rounded-2xl bg-muted" />
            <div className="h-64 animate-pulse rounded-2xl bg-muted" />
          </div>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-6">
          <p className="font-medium text-destructive">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchPlan}>
            Retry
          </Button>
        </div>
      ) : (
        <>
          {/* Current plan + status */}
          <div className="mb-8 rounded-2xl border border-border bg-background p-6">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Current Plan
                </p>
                <p className="mt-0.5 text-xl font-bold">{planData?.plan?.name ?? "Free"}</p>
              </div>
              <div className="flex items-center gap-3">
                {planData?.status && (
                  <span className={["rounded-full px-2.5 py-0.5 text-xs font-medium", statusBadgeClass].join(" ")}>
                    {planData.status.charAt(0).toUpperCase() + planData.status.slice(1)}
                  </span>
                )}
                {planData?.current_period_end && (
                  <p className="text-xs text-muted-foreground">
                    Renews{" "}
                    {new Date(planData.current_period_end).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </p>
                )}
              </div>
            </div>

            {/* Usage bars */}
            <div className="space-y-4">
              <h2 className="text-sm font-semibold">Usage this period</h2>
              <UsageBar
                label="Seats"
                used={usage.seats}
                limit={limits.seat_limit}
              />
              <UsageBar
                label="Generations today"
                used={usage.generations_today}
                limit={limits.generations_per_day_limit}
              />
              <UsageBar
                label="Scans this month"
                used={usage.scans_this_month}
                limit={limits.monthly_scan_limit}
              />
            </div>
          </div>

          {/* Tier cards */}
          <div>
            <h2 className="mb-4 text-lg font-semibold">Plans</h2>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {plans.map((plan) => (
                <PlanCard
                  key={plan.code}
                  plan={plan}
                  currentPlanCode={currentPlanCode}
                  orgId={orgId}
                  onSubscribeSuccess={fetchPlan}
                />
              ))}
            </div>
          </div>

          {/* Note */}
          <p className="mt-6 text-xs text-muted-foreground">
            Payments are processed securely via Razorpay. Subscriptions renew automatically.
            Contact support to cancel.
          </p>
        </>
      )}
    </div>
  )
}
