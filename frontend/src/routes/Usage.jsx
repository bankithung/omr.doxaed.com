import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Users, FileText, ScanLine, ArrowUpRight } from "lucide-react"
import { getPlan } from "@/api/billing"
import { useOrg } from "@/org/OrgContext"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

function pct(used, limit) {
  if (limit == null) return 0 // unlimited
  if (!limit) return used > 0 ? 100 : 0
  return Math.min(100, Math.round((used / limit) * 100))
}

function UsageCard({ icon: Icon, label, used, limit, note }) {
  const unlimited = limit == null
  const percent = pct(used, limit)
  const tone = percent >= 100 ? "bg-destructive" : percent >= 80 ? "bg-warning" : "bg-primary"
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tabular-nums">{used}</span>
        <span className="text-sm text-muted-foreground">
          / {unlimited ? "Unlimited" : limit}
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-3">
        <div
          className={cn("h-full rounded-full transition-all", unlimited ? "bg-success/40" : tone)}
          style={{ width: unlimited ? "8%" : `${percent}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {unlimited ? "Unlimited on this plan" : `${percent}% of your quota`}
        {note ? ` · ${note}` : ""}
      </p>
    </div>
  )
}

// Supabase-style Usage page — quota bars for the current billing cycle, fed by
// the existing GET /billing/organizations/:id/plan/ (plan + limits + live usage).
export default function Usage() {
  const navigate = useNavigate()
  const { activeOrg } = useOrg() ?? {}
  const orgId = activeOrg?.id
  const slug = activeOrg?.slug
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!orgId) return
    setLoading(true)
    try {
      setData(await getPlan(orgId))
    } catch {
      toast.error("Failed to load usage")
    } finally {
      setLoading(false)
    }
  }, [orgId])

  useEffect(() => {
    load()
  }, [load])

  const plan = data?.plan
  const limits = data?.limits ?? {}
  const usage = data?.usage ?? {}

  return (
    <PageShell>
      <PageHeader title="Usage" description={activeOrg?.name} />

      {loading || !data ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
        <>
          {/* Plan banner */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface-2 p-4">
            <div>
              <p className="text-sm font-semibold">
                Organization is on the {plan?.name ?? "Free"} plan
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Usage resets each billing cycle. Exceeding a quota may pause scoped actions
                until you upgrade.
              </p>
            </div>
            <Button variant="outline" onClick={() => navigate(`/org/${slug}/billing`)}>
              <ArrowUpRight className="size-4" aria-hidden="true" /> Change plan
            </Button>
          </div>

          {/* Quota bars */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <UsageCard
              icon={Users}
              label="Members (seats)"
              used={usage.seats ?? 0}
              limit={limits.seat_limit}
            />
            <UsageCard
              icon={FileText}
              label="Sheet generations today"
              used={usage.generations_today ?? 0}
              limit={limits.generations_per_day_limit}
              note="resets daily"
            />
            <UsageCard
              icon={ScanLine}
              label="Scans this cycle"
              used={usage.scans_this_month ?? 0}
              limit={limits.monthly_scan_limit}
            />
          </div>

          <p className="text-xs text-muted-foreground">
            Students per sheet generation is capped at{" "}
            <strong>{limits.students_per_generation_limit ?? "unlimited"}</strong> on this plan.
          </p>
        </>
      )}
    </PageShell>
  )
}
