import { useEffect, useState } from "react"
import { toast } from "sonner"
import { useOrg } from "@/org/OrgContext"
import { listPlans, getPlan, subscribe } from "@/api/billing"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { ErrorState } from "@/components/ui/error-state"
import {
  Card,
  CardHeader,
  CardContent,
} from "@/components/ui/card"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckIcon, ZapIcon, BuildingIcon, UsersIcon, StarIcon } from "lucide-react"

// Human-readable price label. Enterprise is custom-priced (price_inr is 0 as a
// placeholder) so it must read "Custom", not "Free".
function derivePriceLabel(plan) {
  if (plan.code === "enterprise") return "Custom"
  const n = parseFloat(plan.price_inr)
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

// Display order (Enterprise has price 0 as a custom-pricing placeholder, so we
// can't order by price — that would float it to the front next to Free).
const PLAN_ORDER = ["free", "team", "business", "enterprise"]
const planRank = (code) => {
  const i = PLAN_ORDER.indexOf(code)
  return i === -1 ? PLAN_ORDER.length : i
}

// Map subscription status → a Badge status variant.
const STATUS_VARIANT = {
  active: "success",
  trialing: "info",
}

function UsageBar({ label, used, limit }) {
  if (limit === null || limit === undefined) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{label}</span>
          <span className="tabular font-medium">{used ?? 0} / Unlimited</span>
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
            "tabular font-medium",
            isDanger
              ? "text-destructive"
              : isWarning
                ? "text-[var(--color-warning)]"
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
              ? "[&_[data-slot=progress-indicator]]:bg-[var(--color-warning)]"
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
  const priceLabel = derivePriceLabel(plan)
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
        "relative flex flex-col rounded-lg border p-6",
        isHighlight ? "border-primary" : "border-border",
        isCurrent ? "bg-surface-2" : "bg-card",
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
            "flex size-9 items-center justify-center rounded-md",
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
        <span className="tabular text-2xl font-bold">{priceLabel}</span>
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
          <div className="flex items-center justify-center rounded-md border border-border bg-muted py-2 text-sm font-medium text-muted-foreground">
            Current plan
          </div>
        ) : plan.code === "enterprise" ? (
          <Button
            variant="outline"
            className="w-full"
            onClick={() => toast.info("Contact us to set up an Enterprise plan.")}
          >
            Contact sales
          </Button>
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
  const { activeOrg } = useOrg()
  const orgId = activeOrg?.id
  const [planData, setPlanData] = useState(null)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const org = activeOrg

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

  return (
    <PageShell>
      <PageHeader
        title="Billing & subscription"
        description={`Plan and usage for ${org?.name ?? "this organization"}`}
      />

      {loading ? (
        <div className="space-y-8">
          <Skeleton className="h-40 w-full rounded-lg" />
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-64 rounded-lg" />
            ))}
          </div>
        </div>
      ) : error ? (
        <ErrorState
          title="Couldn't load billing"
          description={error}
          onRetry={fetchPlan}
        />
      ) : (
        <>
          {/* Current plan + status */}
          <Card>
            <CardHeader className="flex-wrap gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Current plan
                </p>
                <p className="mt-0.5 text-xl font-bold">
                  {planData?.plan?.name ?? "Free"}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {planData?.status && (
                  <Badge variant={STATUS_VARIANT[planData.status] ?? "warning"}>
                    {planData.status.charAt(0).toUpperCase() +
                      planData.status.slice(1)}
                  </Badge>
                )}
                {planData?.current_period_end && (
                  <p className="tabular text-xs text-muted-foreground">
                    Renews{" "}
                    {new Date(planData.current_period_end).toLocaleDateString(
                      undefined,
                      { year: "numeric", month: "short", day: "numeric" }
                    )}
                  </p>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <h2 className="text-sm font-semibold">Usage this period</h2>
              <UsageBar label="Seats" used={usage.seats} limit={limits.seat_limit} />
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
            </CardContent>
          </Card>

          {/* Tier cards */}
          <section className="space-y-4">
            <h2 className="text-lg font-semibold">Plans</h2>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {[...plans]
                .sort((a, b) => planRank(a.code) - planRank(b.code))
                .map((plan) => (
                <PlanCard
                  key={plan.code}
                  plan={plan}
                  currentPlanCode={currentPlanCode}
                  orgId={orgId}
                  onSubscribeSuccess={fetchPlan}
                />
              ))}
            </div>
          </section>

          {/* Note */}
          <p className="text-xs text-muted-foreground">
            Payments are processed securely via Razorpay. Subscriptions renew
            automatically. Contact support to cancel.
          </p>
        </>
      )}
    </PageShell>
  )
}
