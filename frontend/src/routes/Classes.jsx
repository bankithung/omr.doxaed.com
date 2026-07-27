import { useEffect, useState, useCallback } from "react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { SearchIcon, FolderIcon } from "lucide-react"
import { listClasses } from "@/api/assessments"
import { useOrg } from "@/org/OrgContext"
import { topKindLabel, pluralize } from "@/features/class/typePresets"
import NewClassDialog from "@/features/class/NewClassDialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { Skeleton } from "@/components/ui/skeleton"

// A class card — the "project" tile (Supabase-style). The whole card links into
// the class workspace.
function ClassCard({ cls }) {
  return (
    <Link
      to={`/classes/${cls.id}`}
      className="group flex items-center gap-3 rounded-xl border border-border bg-surface-1 p-4 transition-colors hover:border-indigo/50 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-indigo/10 text-sm font-bold text-indigo">
        {(cls.name?.[0] ?? "C").toUpperCase()}
      </span>
      <div className="min-w-0">
        <p className="truncate font-semibold group-hover:text-indigo">{cls.name}</p>
        <p className="truncate text-xs text-muted-foreground">
          {cls.description || "No description"}
        </p>
      </div>
    </Link>
  )
}

export default function Classes() {
  const navigate = useNavigate()
  const { activeOrg } = useOrg() ?? {}
  // Top-level label adapts to the org type (Class / Department / Course / …).
  const topLabel = topKindLabel(activeOrg?.type)
  const plural = pluralize(topLabel)
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState("")
  const [newOpen, setNewOpen] = useState(false)

  const fetchClasses = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await listClasses({ parent: "none" })
      setClasses(data.results ?? data)
    } catch {
      setError(true)
      toast.error("Failed to load classes")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchClasses()
  }, [fetchClasses])

  const filtered = classes.filter((c) =>
    (c.name ?? "").toLowerCase().includes(query.trim().toLowerCase()),
  )

  return (
    <PageShell>
      <PageHeader
        title={plural}
        description={activeOrg ? `${plural} in ${activeOrg.name}` : `Your ${plural.toLowerCase()}`}
        actions={
          <Button onClick={() => setNewOpen(true)}>New {topLabel.toLowerCase()}</Button>
        }
      />

      {!loading && !error && classes.length > 0 && (
        <div className="relative max-w-sm">
          <SearchIcon
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            placeholder={`Search ${plural.toLowerCase()}…`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
            aria-label={`Search ${plural.toLowerCase()}`}
          />
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px] w-full rounded-xl" />
          ))}
        </div>
      ) : error ? (
        <ErrorState
          title="Couldn't load classes"
          description="Something went wrong while loading your classes."
          onRetry={fetchClasses}
        />
      ) : classes.length === 0 ? (
        <EmptyState
          icon={FolderIcon}
          title={`No ${plural.toLowerCase()} yet`}
          description={`Create your first ${topLabel.toLowerCase()} to start adding exams, students and subjects.`}
          action={<Button onClick={() => setNewOpen(true)}>New {topLabel.toLowerCase()}</Button>}
        />
      ) : filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No {plural.toLowerCase()} match “{query}”.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((cls) => (
            <ClassCard key={cls.id} cls={cls} />
          ))}
        </div>
      )}

      {newOpen && (
        <NewClassDialog
          topLabel={topLabel}
          onClose={() => setNewOpen(false)}
          onCreated={(cls) => {
            setNewOpen(false)
            navigate(`/classes/${cls.id}`)
          }}
        />
      )}
    </PageShell>
  )
}
