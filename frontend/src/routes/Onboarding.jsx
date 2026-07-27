import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { FileText, PenLine, ScanLine, Sparkles, X } from "lucide-react"

import { useOrg } from "@/org/OrgContext"
import { createOrg, invite } from "@/api/orgs"
import { createClass } from "@/api/assessments"
import { Stepper, StepperCompact } from "@/components/ui/stepper"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const ONBOARDED_KEY = "omrflow_onboarded"
const STEP_LABELS = ["Welcome", "Organisation", "Invite", "Class", "Test"]
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Shared wordmark — flat app tokens only, mirrors the auth/legal layouts.
function Wordmark({ className = "" }) {
  return (
    <span
      className={`inline-flex items-baseline gap-1.5 font-bold tracking-tight ${className}`}
    >
      <span className="text-foreground">DoxaEd</span>
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo">
        OMR
      </span>
    </span>
  )
}

// ─── InviteEmails — chips input for collecting member emails ──────────────────
function InviteEmails({ emails, onAdd, onRemove }) {
  const [draft, setDraft] = useState("")
  const [error, setError] = useState("")

  function commit() {
    const value = draft.trim().replace(/,$/, "").trim()
    if (!value) return
    if (!EMAIL_RE.test(value)) {
      setError("Enter a valid email")
      return
    }
    if (emails.includes(value)) {
      setError("Already added")
      return
    }
    onAdd(value)
    setDraft("")
    setError("")
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      commit()
    }
  }

  return (
    <div className="space-y-1.5">
      <Label htmlFor="invite-emails">Teammate emails</Label>
      {emails.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {emails.map((email) => (
            <li
              key={email}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-muted px-2.5 py-1 text-sm"
            >
              <span className="truncate max-w-[200px]">{email}</span>
              <button
                type="button"
                onClick={() => onRemove(email)}
                className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
                aria-label={`Remove ${email}`}
              >
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <Input
        id="invite-emails"
        type="email"
        placeholder="colleague@example.com"
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value)
          if (error) setError("")
        }}
        onKeyDown={handleKeyDown}
        onBlur={commit}
        className="h-11"
        aria-invalid={!!error}
      />
      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : (
        <p className="text-xs text-muted-foreground">Press Enter to add each email.</p>
      )}
    </div>
  )
}

// ─── Onboarding wizard ────────────────────────────────────────────────────────
export default function Onboarding() {
  const navigate = useNavigate()
  const { refreshOrgs, setActiveOrg } = useOrg()

  const [step, setStep] = useState(0)

  // Step 1 — organisation
  const [orgName, setOrgName] = useState("")
  const [orgError, setOrgError] = useState("")
  const [creatingOrg, setCreatingOrg] = useState(false)
  const [orgId, setOrgId] = useState(null)

  // Step 2 — invites
  const [emails, setEmails] = useState([])
  const [role, setRole] = useState("member")
  const [sendingInvites, setSendingInvites] = useState(false)

  // Step 3 — first class
  const [className, setClassName] = useState("")
  const [classError, setClassError] = useState("")
  const [creatingClass, setCreatingClass] = useState(false)
  const [classId, setClassId] = useState(null)

  function next() {
    setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1))
  }

  // Mark onboarded (completion AND skip) then leave the wizard.
  function finish(to = "/dashboard") {
    try {
      localStorage.setItem(ONBOARDED_KEY, "1")
    } catch { /* ignore storage failures */ }
    navigate(to, { replace: true })
  }

  // ── Step 1: create organisation ─────────────────────────────────────────────
  async function handleCreateOrg() {
    if (!orgName.trim()) {
      setOrgError("Organisation name is required")
      return
    }
    setCreatingOrg(true)
    setOrgError("")
    try {
      const org = await createOrg(orgName.trim())
      setOrgId(org.id)
      await refreshOrgs({ force: true })
      setActiveOrg(String(org.id))
      next()
    } catch (err) {
      setOrgError(err?.response?.data?.detail || "Could not create organisation")
    } finally {
      setCreatingOrg(false)
    }
  }

  // ── Step 2: send invites ────────────────────────────────────────────────────
  async function handleSendInvites() {
    // Without an org there is nothing to invite into — advance gracefully.
    if (!orgId || emails.length === 0) {
      next()
      return
    }
    setSendingInvites(true)
    try {
      await Promise.allSettled(emails.map((email) => invite(orgId, email, role)))
      next()
    } finally {
      setSendingInvites(false)
    }
  }

  // ── Step 3: create first class ──────────────────────────────────────────────
  async function handleCreateClass() {
    if (!className.trim()) {
      setClassError("Class name is required")
      return
    }
    setCreatingClass(true)
    setClassError("")
    try {
      const cls = await createClass({ name: className.trim(), description: "" })
      setClassId(cls.id)
      next()
    } catch (err) {
      setClassError(err?.response?.data?.detail || "Could not create class")
    } finally {
      setCreatingClass(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Top bar: brand + persistent skip */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <Wordmark className="text-base" />
        <Button
          variant="ghost"
          size="sm"
          className="min-h-[40px]"
          onClick={() => finish()}
        >
          Skip for now
        </Button>
      </header>

      <main className="flex flex-1 items-start justify-center px-4 py-8 sm:items-center">
        <div className="w-full max-w-md space-y-6">
          {/* Progress: full stepper on sm+, compact on mobile */}
          <Stepper
            steps={STEP_LABELS}
            current={step}
            className="hidden justify-center gap-2 sm:flex sm:gap-4"
          />
          <StepperCompact steps={STEP_LABELS} current={step} className="sm:hidden" />

          {/* Step 0 — Welcome */}
          {step === 0 && (
            <Card>
              <CardContent className="space-y-6 p-6 text-center sm:p-8">
                <span className="mx-auto flex size-14 items-center justify-center rounded-2xl border border-border bg-muted text-indigo">
                  <Sparkles className="size-7" aria-hidden="true" />
                </span>
                <div className="space-y-2">
                  <h1 className="text-2xl font-bold tracking-tight">Welcome to DoxaEd OMR</h1>
                  <p className="text-sm text-muted-foreground">Let's set up your workspace.</p>
                </div>
                <Button className="h-11 w-full" onClick={next}>
                  Get started
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Step 1 — Create organisation */}
          {step === 1 && (
            <Card>
              <CardContent className="space-y-6 p-6 sm:p-8">
                <div className="space-y-2 text-center">
                  <h1 className="text-2xl font-bold tracking-tight">Create your organisation</h1>
                  <p className="text-sm text-muted-foreground">Group your team's grading.</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="org-name">Organisation name</Label>
                  <Input
                    id="org-name"
                    placeholder="e.g. Springfield School"
                    value={orgName}
                    onChange={(e) => {
                      setOrgName(e.target.value)
                      if (orgError) setOrgError("")
                    }}
                    className="h-11"
                    aria-invalid={!!orgError}
                    autoFocus
                  />
                  {orgError && <p className="text-sm text-destructive">{orgError}</p>}
                </div>
                <div className="space-y-3">
                  <Button
                    className="h-11 w-full"
                    onClick={handleCreateOrg}
                    disabled={creatingOrg}
                  >
                    {creatingOrg ? "Creating…" : "Create organisation"}
                  </Button>
                  <Button
                    variant="ghost"
                    className="h-11 w-full"
                    onClick={next}
                    disabled={creatingOrg}
                  >
                    Just me for now
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 2 — Invite members */}
          {step === 2 && (
            <Card>
              <CardContent className="space-y-6 p-6 sm:p-8">
                <div className="space-y-2 text-center">
                  <h1 className="text-2xl font-bold tracking-tight">Invite your team</h1>
                  <p className="text-sm text-muted-foreground">Add teachers to grade together.</p>
                </div>

                {orgId ? (
                  <>
                    <InviteEmails
                      emails={emails}
                      onAdd={(email) => setEmails((prev) => [...prev, email])}
                      onRemove={(email) =>
                        setEmails((prev) => prev.filter((e) => e !== email))
                      }
                    />
                    <div className="space-y-1.5">
                      <Label htmlFor="invite-role">Role</Label>
                      <Select value={role} onValueChange={setRole}>
                        <SelectTrigger id="invite-role" className="h-11 w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="member">Member</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-3">
                      <Button
                        className="h-11 w-full"
                        onClick={handleSendInvites}
                        disabled={sendingInvites}
                      >
                        {sendingInvites ? "Sending…" : "Send invites"}
                      </Button>
                      <Button
                        variant="ghost"
                        className="h-11 w-full"
                        onClick={next}
                        disabled={sendingInvites}
                      >
                        Skip
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-center text-sm text-muted-foreground">
                      Create an organisation first to invite teammates.
                    </p>
                    <Button className="h-11 w-full" onClick={next}>
                      Continue
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Step 3 — First class */}
          {step === 3 && (
            <Card>
              <CardContent className="space-y-6 p-6 sm:p-8">
                <div className="space-y-2 text-center">
                  <h1 className="text-2xl font-bold tracking-tight">Create your first class</h1>
                  <p className="text-sm text-muted-foreground">Classes hold your tests.</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="onb-class-name">Class name</Label>
                  <Input
                    id="onb-class-name"
                    placeholder="e.g. Class 8A"
                    value={className}
                    onChange={(e) => {
                      setClassName(e.target.value)
                      if (classError) setClassError("")
                    }}
                    className="h-11"
                    aria-invalid={!!classError}
                    autoFocus
                  />
                  {classError ? (
                    <p className="text-sm text-destructive">{classError}</p>
                  ) : (
                    <p className="text-xs text-muted-foreground">You can rename it later.</p>
                  )}
                </div>
                <div className="space-y-3">
                  <Button
                    className="h-11 w-full"
                    onClick={handleCreateClass}
                    disabled={creatingClass}
                  >
                    {creatingClass ? "Creating…" : "Create class"}
                  </Button>
                  <Button
                    variant="ghost"
                    className="h-11 w-full"
                    onClick={next}
                    disabled={creatingClass}
                  >
                    Skip
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Step 4 — First test */}
          {step === 4 && (
            <Card>
              <CardContent className="space-y-6 p-6 sm:p-8">
                <div className="space-y-2 text-center">
                  <h1 className="text-2xl font-bold tracking-tight">Build your first test</h1>
                  <p className="text-sm text-muted-foreground">Start blank or do this later.</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => {
                      // Mark onboarded, then hand off to the real test wizard.
                      if (classId) finish(`/classes/${classId}/tests/new`)
                      else finish("/classes")
                    }}
                    className="flex min-h-[40px] flex-col items-center gap-2 rounded-xl border border-border bg-background p-5 text-center transition-colors hover:border-indigo/40 hover:bg-muted"
                  >
                    <PenLine className="size-6 text-indigo" aria-hidden="true" />
                    <span className="text-base font-semibold">Start blank</span>
                    <span className="text-sm text-muted-foreground">Add questions now.</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => finish()}
                    className="flex min-h-[40px] flex-col items-center gap-2 rounded-xl border border-border bg-background p-5 text-center transition-colors hover:border-indigo/40 hover:bg-muted"
                  >
                    <FileText className="size-6 text-muted-foreground" aria-hidden="true" />
                    <span className="text-base font-semibold">Skip</span>
                    <span className="text-sm text-muted-foreground">Finish setup.</span>
                  </button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </main>

      {/* Subtle brand footer mark — flat, app tokens. */}
      <footer className="flex items-center justify-center gap-1.5 px-4 pb-6 text-xs text-muted-foreground">
        <ScanLine className="size-3.5" aria-hidden="true" />
        <span>Scan &amp; auto-grade OMR exams in minutes</span>
      </footer>
    </div>
  )
}
