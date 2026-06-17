import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { toast } from "sonner"
import { acceptInvite } from "@/api/orgs"
import { useOrg } from "@/org/OrgContext"
import { Button } from "@/components/ui/button"

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
        refreshOrgs()
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

  if (status === "loading") {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <p className="text-muted-foreground">Accepting your invitation…</p>
      </div>
    )
  }

  if (status === "error") {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center space-y-4">
        <h1 className="text-2xl font-bold text-destructive">Invitation failed</h1>
        <p className="text-sm text-muted-foreground">{errorMsg}</p>
        <Button asChild variant="outline">
          <Link to="/organizations">Go to Organizations</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-md px-4 py-20 text-center space-y-4">
      <h1 className="text-2xl font-bold">You're in!</h1>
      <p className="text-sm text-muted-foreground">
        {orgName
          ? `You've joined ${orgName}.`
          : "You've successfully joined the organization."}
      </p>
      <Button asChild>
        <Link to="/organizations">View Organizations</Link>
      </Button>
    </div>
  )
}
