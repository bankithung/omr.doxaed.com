import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { toast } from "sonner"
import { CheckCircle2, Loader2, XCircle } from "lucide-react"
import { acceptInvite } from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { Button } from "@/components/ui/button"
import AuthLayout from "@/components/auth/AuthLayout"

export default function AcceptInvite() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token")
  const { refreshOrgs } = useOrg()

  const [status, setStatus] = useState("loading") // "loading" | "success" | "error"
  const [orgName, setOrgName] = useState("")
  const [errorMsg, setErrorMsg] = useState("")

  useEffect(() => {
    if (!token) {
      setStatus("error")
      setErrorMsg("No invitation token found in the URL.")
      return
    }

    acceptInvite(token)
      .then((data) => {
        setOrgName(data?.organization?.name ?? data?.org_name ?? "")
        setStatus("success")
        toast.success("Invitation accepted!")
        refreshOrgs({ force: true })
      })
      .catch((err) => {
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.token?.[0] ||
          "Failed to accept invitation. The link may have expired or already been used."
        setErrorMsg(msg)
        setStatus("error")
        toast.error(msg)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const subtitle =
    status === "loading"
      ? "Confirming your invitation."
      : status === "success"
        ? "Welcome to the team."
        : "We couldn't accept this invitation."

  return (
    <AuthLayout title="Accept invitation" subtitle={subtitle}>
      {status === "loading" && (
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <Loader2 className="size-8 animate-spin text-primary" aria-hidden="true" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold">Accepting…</h2>
            <p className="text-sm text-muted-foreground">
              Hang tight while we add you to the organization.
            </p>
          </div>
        </div>
      )}

      {status === "success" && (
        <div className="space-y-5">
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-[color-mix(in_oklch,var(--color-success)_14%,transparent)]">
              <CheckCircle2 className="size-7 text-[var(--color-success)]" aria-hidden="true" />
            </span>
            <div className="space-y-1">
              <h2 className="text-lg font-bold">You're in!</h2>
              <p className="text-sm text-muted-foreground">
                {orgName
                  ? `You've joined ${orgName}.`
                  : "You've successfully joined the organization."}
              </p>
            </div>
          </div>
          <Button asChild className="h-11 w-full">
            <Link to="/organizations">View Organizations</Link>
          </Button>
        </div>
      )}

      {status === "error" && (
        <div className="space-y-5">
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10">
              <XCircle className="size-7 text-destructive" aria-hidden="true" />
            </span>
            <div className="space-y-1">
              <h2 className="text-lg font-bold">Invitation failed</h2>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </div>
          <Button asChild variant="outline" className="h-11 w-full">
            <Link to="/organizations">Go to Organizations</Link>
          </Button>
        </div>
      )}
    </AuthLayout>
  )
}
