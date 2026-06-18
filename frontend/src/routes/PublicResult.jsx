/**
 * PublicResult — the student-facing result portal page.
 * This is a STANDALONE full-page layout with NO app Nav or auth.
 * App.jsx suppresses <Nav/> for paths starting with /r/.
 */
import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { getPortalMeta, lookupResult, getLeaderboard } from "@/api/public"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// ────────────────────────────────────────────────
// Result card
// ────────────────────────────────────────────────

function ResultCard({ result }) {
  const { name, roll_number, score, max_score, percentile, rank } = result
  const pct = max_score > 0 ? Math.round((score / max_score) * 100) : 0
  const colour =
    pct >= 70
      ? "bg-green-100 text-green-800 border-green-200"
      : pct >= 40
        ? "bg-yellow-100 text-yellow-800 border-yellow-200"
        : "bg-red-100 text-red-800 border-red-200"

  return (
    <div className="mt-6 rounded-xl border bg-card p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-lg font-semibold">{name || "—"}</p>
          <p className="text-sm text-muted-foreground">Roll: {roll_number}</p>
        </div>
        <div
          className={`rounded-full border px-4 py-2 text-2xl font-bold tabular-nums ${colour}`}
          aria-label={`Score ${score} out of ${max_score}`}
        >
          {score}/{max_score}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile label="Percentage" value={`${pct}%`} />
        {percentile != null && (
          <StatTile label="Percentile" value={`${Math.round(percentile * 10) / 10}`} />
        )}
        {rank != null && (
          <StatTile label="Rank" value={`#${rank}`} />
        )}
      </div>
    </div>
  )
}

function StatTile({ label, value }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border bg-muted/40 p-3">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-xl font-bold tabular-nums">{value}</span>
    </div>
  )
}

// ────────────────────────────────────────────────
// Leaderboard section
// ────────────────────────────────────────────────

function LeaderboardSection({ slug }) {
  const [rows, setRows] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getLeaderboard(slug)
      .then(setRows)
      .catch((err) => {
        const msg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          "Failed to load leaderboard."
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) {
    return <p className="mt-8 text-sm text-muted-foreground">Loading leaderboard…</p>
  }

  if (error) {
    return <p className="mt-8 text-sm text-destructive">{error}</p>
  }

  if (!rows || rows.length === 0) {
    return <p className="mt-8 text-sm text-muted-foreground">Leaderboard is empty.</p>
  }

  return (
    <div className="mt-8">
      <h2 className="mb-3 text-base font-semibold">Leaderboard</h2>
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2.5">Rank</th>
              <th className="px-4 py-2.5">Name</th>
              <th className="px-4 py-2.5">Score</th>
              <th className="px-4 py-2.5">Percentile</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b last:border-0 hover:bg-muted/20"
              >
                <td className="px-4 py-2.5 font-mono text-muted-foreground">#{row.rank}</td>
                <td className="px-4 py-2.5 font-medium">{row.name || "—"}</td>
                <td className="px-4 py-2.5 tabular-nums">{row.score}</td>
                <td className="px-4 py-2.5 tabular-nums">
                  {row.percentile != null ? `${Math.round(row.percentile * 10) / 10}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────
// Main page
// ────────────────────────────────────────────────

export default function PublicResult() {
  const { slug } = useParams()

  // Portal meta (test info)
  const [meta, setMeta] = useState(null)
  const [metaLoading, setMetaLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  // Lookup form
  const [rollNumber, setRollNumber] = useState("")
  const [accessCode, setAccessCode] = useState("")
  const [looking, setLooking] = useState(false)
  const [result, setResult] = useState(null)
  const [lookupError, setLookupError] = useState(null)

  // Load portal meta on mount
  useEffect(() => {
    getPortalMeta(slug)
      .then(setMeta)
      .catch((err) => {
        if (err.response?.status === 404) {
          setNotFound(true)
        } else {
          setNotFound(true)
        }
      })
      .finally(() => setMetaLoading(false))
  }, [slug])

  async function handleLookup(e) {
    e.preventDefault()
    if (!rollNumber.trim()) return
    setLooking(true)
    setResult(null)
    setLookupError(null)
    try {
      const data = await lookupResult(slug, rollNumber.trim(), accessCode.trim() || undefined)
      setResult(data)
    } catch (err) {
      const status = err.response?.status
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        null

      if (status === 403) {
        setLookupError("Invalid access code. Please check and try again.")
      } else if (status === 404) {
        setLookupError("No result found for this roll number.")
      } else if (status === 429) {
        setLookupError("Too many requests. Please wait a moment and try again.")
      } else {
        setLookupError(detail || "Something went wrong. Please try again.")
      }
    } finally {
      setLooking(false)
    }
  }

  // ── Loading state ──
  if (metaLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  // ── Not published / not found ──
  if (notFound || !meta) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
        <div className="mb-4 text-4xl" aria-hidden="true">🔒</div>
        <h1 className="mb-2 text-xl font-semibold">Results link not available</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          This results link is either inactive or doesn't exist. If you received this link
          from your teacher, please ask them to verify it's published.
        </p>
      </div>
    )
  }

  const { test_title, org_name, access_mode, show_leaderboard } = meta
  const requiresCode = access_mode === "code"

  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ── */}
      <header className="border-b bg-card px-4 py-5 text-center sm:py-7">
        {org_name && (
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            {org_name}
          </p>
        )}
        <h1 className="text-2xl font-bold sm:text-3xl">{test_title || "Results"}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter your roll number to look up your result
        </p>
      </header>

      {/* ── Main content ── */}
      <main className="mx-auto max-w-lg px-4 py-8">
        {/* Lookup form */}
        <form onSubmit={handleLookup} aria-label="Result lookup form" className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="roll_number">Roll number</Label>
            <Input
              id="roll_number"
              type="text"
              placeholder="e.g. 2024001"
              value={rollNumber}
              onChange={(e) => setRollNumber(e.target.value)}
              autoComplete="off"
              required
              aria-required="true"
            />
          </div>

          {requiresCode && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="access_code">Access code</Label>
              <Input
                id="access_code"
                type="text"
                placeholder="Enter the access code from your teacher"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                autoComplete="off"
              />
            </div>
          )}

          <Button type="submit" disabled={looking || !rollNumber.trim()} className="w-full">
            {looking ? "Looking up…" : "Get result"}
          </Button>
        </form>

        {/* Lookup error */}
        {lookupError && (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            {lookupError}
          </div>
        )}

        {/* Result card */}
        {result && <ResultCard result={result} />}

        {/* Leaderboard */}
        {show_leaderboard && <LeaderboardSection slug={slug} />}

        {/* Privacy note */}
        <p className="mt-8 text-center text-xs text-muted-foreground">
          Results are visible to anyone with this link who enters a valid roll number.
        </p>
      </main>
    </div>
  )
}
