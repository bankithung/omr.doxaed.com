import { useMemo, useState } from "react"
import { ChevronUpIcon, ChevronDownIcon, ChevronsUpDownIcon } from "lucide-react"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { ActionMenu } from "@/components/ui/action-menu"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { TableSkeleton } from "@/components/ui/skeletons"
import { cn } from "@/lib/utils"

/**
 * SortableHead — a 3-state (none → asc → desc) sortable column header.
 * Drives aria-sort for a11y.
 */
function SortableHead({ label, sortKey, sort, onSortChange, className }) {
  const active = sort?.key === sortKey
  const dir = active ? sort.dir : null
  const ariaSort = !active ? "none" : dir === "asc" ? "ascending" : "descending"
  const Icon = !active ? ChevronsUpDownIcon : dir === "asc" ? ChevronUpIcon : ChevronDownIcon

  function cycle() {
    if (!active) onSortChange({ key: sortKey, dir: "asc" })
    else if (dir === "asc") onSortChange({ key: sortKey, dir: "desc" })
    else onSortChange(null)
  }

  return (
    <TableHead aria-sort={ariaSort} className={className}>
      <button
        type="button"
        onClick={cycle}
        className="-ml-1 inline-flex items-center gap-1 rounded px-1 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        {label}
        <Icon className={cn("size-3.5", active ? "text-foreground" : "text-muted-foreground/60")} aria-hidden="true" />
      </button>
    </TableHead>
  )
}

/**
 * DataTable — a flat, Supabase-grade table on top of the base Table primitive.
 *
 * Features: sticky muted header, 44px rows, optional row selection + bulk bar,
 * per-row kebab (ActionMenu), 3-state sortable heads, and the loading / error /
 * empty per-surface contract. Below md it degrades to a stacked card list (the
 * same pattern DataList uses) so it stays mobile-first.
 *
 * Props:
 *   columns: Array<{
 *     key, header?, cell:(row)=>node, className?, sortable?:bool,
 *     mobileLabel?, hideOnMobile?
 *   }>
 *   rows, getRowKey:(row)=>key
 *   loading?:bool, error?:bool, onRetry?:fn
 *   empty?: { icon?, title, description?, action? }  — EmptyState props
 *   selectable?:bool, selectedKeys?:Set, onSelectionChange?:(Set)=>void
 *   bulkActions?: ReactNode   — rendered in the bulk bar (right side)
 *   rowActions?: (row)=>Array — ActionMenu items per row (kebab column)
 *   sort?, onSortChange?      — controlled sort state
 *   onRowClick?:(row)=>void
 */
function DataTable({
  columns = [],
  rows = [],
  getRowKey = (r) => r.id,
  loading = false,
  error = false,
  onRetry,
  empty,
  selectable = false,
  selectedKeys,
  onSelectionChange,
  bulkActions,
  rowActions,
  sort,
  onSortChange,
  onRowClick,
  className,
}) {
  // Uncontrolled fallback for selection.
  const [internalSel, setInternalSel] = useState(() => new Set())
  const selection = selectedKeys ?? internalSel
  const setSelection = onSelectionChange ?? setInternalSel

  const allKeys = useMemo(() => rows.map((r) => getRowKey(r)), [rows, getRowKey])
  const allSelected = allKeys.length > 0 && allKeys.every((k) => selection.has(k))
  const someSelected = allKeys.some((k) => selection.has(k))

  function toggleAll() {
    setSelection(allSelected ? new Set() : new Set(allKeys))
  }
  function toggleRow(key) {
    const next = new Set(selection)
    next.has(key) ? next.delete(key) : next.add(key)
    setSelection(next)
  }

  if (loading) return <TableSkeleton className={className} />
  if (error)
    return (
      <ErrorState
        className={className}
        onRetry={onRetry}
        description="Something went wrong loading this list."
      />
    )
  if (rows.length === 0)
    return (
      <EmptyState
        className={cn("rounded-lg border border-border", className)}
        icon={empty?.icon}
        title={empty?.title ?? "Nothing here yet"}
        description={empty?.description}
        action={empty?.action}
      />
    )

  const hasKebab = typeof rowActions === "function"
  const selectedCount = allKeys.filter((k) => selection.has(k)).length

  return (
    <div data-slot="data-table" className={cn("w-full", className)}>
      {/* Bulk selection bar */}
      {selectable && selectedCount > 0 && (
        <div className="flex h-11 items-center gap-3 rounded-t-lg border border-border bg-surface-2 px-3">
          <span className="text-sm font-medium tabular">{selectedCount} selected</span>
          <div className="ml-auto flex items-center gap-2">{bulkActions}</div>
        </div>
      )}

      {/* ── Table (md+) ── */}
      <div className={cn("hidden overflow-hidden border border-border md:block", selectedCount > 0 ? "rounded-b-lg border-t-0" : "rounded-lg")}>
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              {selectable && (
                <TableHead className="sticky top-0 z-10 h-9 w-[44px] bg-surface-1 px-3">
                  <Checkbox
                    checked={allSelected ? true : someSelected ? "indeterminate" : false}
                    onCheckedChange={toggleAll}
                    aria-label="Select all rows"
                  />
                </TableHead>
              )}
              {columns.map((col) =>
                col.sortable && onSortChange ? (
                  <SortableHead
                    key={col.key}
                    label={col.header ?? col.key}
                    sortKey={col.key}
                    sort={sort}
                    onSortChange={onSortChange}
                    className={cn(
                      "sticky top-0 z-10 h-9 bg-surface-1 px-3 text-xs font-medium text-muted-foreground",
                      col.className
                    )}
                  />
                ) : (
                  <TableHead
                    key={col.key}
                    className={cn(
                      "sticky top-0 z-10 h-9 bg-surface-1 px-3 text-xs font-medium text-muted-foreground",
                      col.className
                    )}
                  >
                    {col.header ?? col.key}
                  </TableHead>
                )
              )}
              {hasKebab && (
                <TableHead className="sticky top-0 z-10 h-9 w-10 bg-surface-1 px-3" />
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const key = getRowKey(row)
              const selected = selection.has(key)
              return (
                <TableRow
                  key={key}
                  data-state={selected ? "selected" : undefined}
                  className={cn("group/row", onRowClick && "cursor-pointer")}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {selectable && (
                    <TableCell className="h-11 w-[44px] px-3 py-0" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selected}
                        onCheckedChange={() => toggleRow(key)}
                        aria-label="Select row"
                      />
                    </TableCell>
                  )}
                  {columns.map((col) => (
                    <TableCell key={col.key} className={cn("h-11 px-3 py-0", col.className)}>
                      {col.cell(row)}
                    </TableCell>
                  ))}
                  {hasKebab && (
                    <TableCell className="h-11 w-10 px-3 py-0 text-right" onClick={(e) => e.stopPropagation()}>
                      <span className="opacity-0 transition-opacity group-hover/row:opacity-100 focus-within:opacity-100">
                        <ActionMenu items={rowActions(row)} triggerLabel="Row actions" />
                      </span>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {/* ── Card list (<md) ── */}
      <div className="flex flex-col gap-3 md:hidden">
        {rows.map((row) => {
          const key = getRowKey(row)
          return (
            <div
              key={key}
              role={onRowClick ? "button" : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              onClick={
                onRowClick
                  ? (e) => {
                      // Ignore clicks that originate inside the row-actions kebab.
                      if (e.target.closest("[data-row-actions]")) return
                      onRowClick(row)
                    }
                  : undefined
              }
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault()
                        onRowClick(row)
                      }
                    }
                  : undefined
              }
              className={cn(
                "rounded-lg border border-border bg-card px-4 py-3",
                onRowClick && "cursor-pointer transition-colors hover:bg-muted/50"
              )}
            >
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  {columns
                    .filter((col) => !col.hideOnMobile)
                    .map((col) => {
                      const label =
                        col.mobileLabel ??
                        (typeof col.header === "string" ? col.header : col.key)
                      return (
                        <div
                          key={col.key}
                          className="flex items-baseline justify-between gap-2 py-0.5"
                        >
                          {label && (
                            <span className="shrink-0 text-xs text-muted-foreground">{label}</span>
                          )}
                          <span className="text-right text-sm">{col.cell(row)}</span>
                        </div>
                      )
                    })}
                </div>
                {hasKebab && (
                  <span data-row-actions>
                    <ActionMenu items={rowActions(row)} triggerLabel="Row actions" />
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export { DataTable, SortableHead }
