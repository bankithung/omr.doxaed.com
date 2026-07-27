import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import {
  User,
  School,
  GraduationCap,
  Landmark,
  Presentation,
  Shapes,
  Check,
} from "lucide-react"
import { createOrg } from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

// Org types — each seeds the default level labels for the group tree.
const TYPES = [
  { value: "personal", label: "Personal", icon: User, structure: "Just groups" },
  { value: "school", label: "School", icon: School, structure: "Classes › Sections" },
  { value: "college", label: "College", icon: GraduationCap, structure: "Courses › Years" },
  { value: "university", label: "University", icon: Landmark, structure: "Departments › Programs" },
  { value: "coaching", label: "Coaching", icon: Presentation, structure: "Batches › Sections" },
  { value: "other", label: "Other", icon: Shapes, structure: "Custom groups" },
]

const PLANS = [
  { value: "free", name: "Free", price: "₹0", caps: ["1 seat", "50 students", "5 exams/mo"] },
  { value: "pro", name: "Pro", price: "₹1,000/mo", caps: ["5 seats", "500 students", "50 exams/mo"] },
  { value: "business", name: "Business", price: "₹2,000/mo", caps: ["20 seats", "2,000 students", "200 exams/mo"] },
  { value: "enterprise", name: "Enterprise", price: "Custom", caps: ["Unlimited", "SSO", "Priority support"] },
]

// Display value → backend plan code ("Pro" is stored as "team").
const PLAN_CODE = { free: "free", pro: "team", business: "business", enterprise: "enterprise" }

export default function NewOrganization() {
  const navigate = useNavigate()
  const { setActiveOrg, refreshOrgs } = useOrg()
  const [name, setName] = useState("")
  const [type, setType] = useState("school")
  const [plan, setPlan] = useState("free")
  const [submitting, setSubmitting] = useState(false)

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Organization name is required")
      return
    }
    setSubmitting(true)
    try {
      // Send the selected plan. Locally (dev) it's applied immediately so you can
      // test plan limits; in production paid plans activate only after Razorpay
      // payment. "Pro" is stored as "team".
      const org = await createOrg({ name: name.trim(), type, plan: PLAN_CODE[plan] ?? plan })
      await refreshOrgs({ force: true })
      setActiveOrg(String(org.id))
      const planName = PLANS.find((p) => p.value === plan)?.name
      toast.success(
        plan === "free" ? "Organization created" : `Organization created on the ${planName} plan`,
      )
      navigate(`/org/${org.slug}`)
    } catch {
      toast.error("Could not create organization")
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas px-4 py-10">
 <div className="mx-auto w-full ">
        <div className="mb-8">
          <p className="text-sm font-bold tracking-tight text-indigo">DoxaEd OMR</p>
          <h1 className="mt-3 text-2xl font-bold tracking-tight">Create your organization</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your classes, exams, students and team live inside an organization.
          </p>
        </div>

        <form onSubmit={handleCreate} className="space-y-8">
          {/* Name */}
          <div className="space-y-1.5">
            <Label htmlFor="org-name">Organization name</Label>
            <Input
              id="org-name"
              placeholder="e.g. Springfield High School"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Type */}
          <div className="space-y-2">
            <Label>Type</Label>
            <p className="text-xs text-muted-foreground">
              Sets the default names for your structure, you can rename and nest anything later.
            </p>
            <div role="radiogroup" aria-label="Organization type" className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {TYPES.map((t) => {
                const on = type === t.value
                const Icon = t.icon
                return (
                  <button
                    key={t.value}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => setType(t.value)}
                    className={cn(
                      "flex min-h-[40px] flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors",
                      on
                        ? "border-indigo ring-1 ring-primary bg-indigo/5"
                        : "border-border bg-surface-1 hover:border-indigo/50",
                    )}
                  >
                    <Icon className={cn("size-5", on ? "text-indigo" : "text-muted-foreground")} aria-hidden="true" />
                    <span className="text-sm font-medium">{t.label}</span>
                    <span className="text-xs text-muted-foreground">{t.structure}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Plan */}
          <div className="space-y-2">
            <Label>Plan</Label>
            <div role="radiogroup" aria-label="Plan" className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {PLANS.map((p) => {
                const on = plan === p.value
                return (
                  <button
                    key={p.value}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => setPlan(p.value)}
                    className={cn(
                      "flex flex-col gap-1 rounded-lg border p-4 text-left transition-colors",
                      on
                        ? "border-indigo ring-1 ring-primary bg-indigo/5"
                        : "border-border bg-surface-1 hover:border-indigo/50",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold">{p.name}</span>
                      <span className="flex items-center gap-1.5">
                        <span className="text-sm font-medium tabular-nums">{p.price}</span>
                        {on && <Check className="size-4 text-indigo" aria-hidden="true" />}
                      </span>
                    </div>
                    <ul className="text-xs text-muted-foreground">
                      {p.caps.map((c) => (
                        <li key={c}>· {c}</li>
                      ))}
                    </ul>
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Paid plans are activated in Billing after your organization is created.
            </p>
          </div>

          <div className="flex gap-2">
            <Button type="submit" disabled={submitting || !name.trim()} className="min-h-[44px]">
              {submitting ? "Creating…" : "Create organization"}
            </Button>
            <Button type="button" variant="ghost" className="min-h-[44px]" onClick={() => navigate("/organizations")}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
