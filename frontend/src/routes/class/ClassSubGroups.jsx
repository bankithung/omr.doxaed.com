import { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { listClasses, createClass } from "@/api/assessments"
import { useClass } from "@/features/class/useClass"
import { useOrg } from "@/org/OrgContext"
import { childKindLabel, pluralize } from "@/features/class/typePresets"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageShell } from "@/components/ui/page-shell"
import { PageHeader } from "@/components/ui/page-header"
import { Skeleton } from "@/components/ui/skeleton"

// The recursive "sub-groups" section of a group workspace. Label adapts to the
// org type (a school Class → "Sections", a university Department → "Programs").
// Opening a child enters its own workspace (same pages, one level deeper).
export default function ClassSubGroups() {
  const { id } = useParams()
  const navigate = useNavigate()
  const cls = useClass(id)
  const { activeOrg } = useOrg() ?? {}
  const childLabel = childKindLabel(activeOrg?.type, cls?.kind_label)
  const plural = pluralize(childLabel)

  const [children, setChildren] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState("")
  const [adding, setAdding] = useState(false)

  const fetchChildren = useCallback(async () => {
    setLoading(true)
    try {
      const d = await listClasses({ parent: id })
      setChildren(d.results ?? d)
    } catch {
      toast.error("Failed to load sub-groups")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchChildren()
  }, [fetchChildren])

  async function handleAdd(e) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error(`${childLabel} name is required`)
      return
    }
    setAdding(true)
    try {
      await createClass({ name: name.trim(), parent: id, kind_label: childLabel })
      setName("")
      toast.success(`${childLabel} added`)
      fetchChildren()
    } catch (err) {
      toast.error(err?.response?.data?.detail || `Failed to add ${childLabel.toLowerCase()}`)
    } finally {
      setAdding(false)
    }
  }

  return (
    <PageShell>
      <PageHeader title={plural} description={cls?.name} />
      <p className="text-sm text-muted-foreground">
        {plural} organize this {cls?.kind_label?.toLowerCase() || "group"} further.
        Open one to manage its own students, subjects and exams.
      </p>

      <form onSubmit={handleAdd} className="flex items-center gap-2">
        <Input
          placeholder={`e.g. ${childLabel} A`}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 sm:max-w-sm"
          aria-label={`New ${childLabel} name`}
        />
        <Button type="submit" size="sm" className="min-h-[40px]" disabled={adding}>
          {adding ? "Adding…" : `Add ${childLabel.toLowerCase()}`}
        </Button>
      </form>

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[60px] w-full rounded-xl" />
          ))}
        </div>
      ) : children.length === 0 ? (
        <p className="text-sm text-muted-foreground">No {plural.toLowerCase()} yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {children.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => navigate(`/classes/${c.id}`)}
              className="group flex items-center gap-3 rounded-xl border border-border bg-surface-1 p-4 text-left transition-colors hover:border-primary/50 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-sm font-bold text-primary">
                {(c.name?.[0] ?? "?").toUpperCase()}
              </span>
              <div className="min-w-0">
                <p className="truncate font-semibold group-hover:text-primary">{c.name}</p>
                <p className="truncate text-xs text-muted-foreground">{c.kind_label || childLabel}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </PageShell>
  )
}
