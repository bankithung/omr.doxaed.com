import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

/**
 * DataList — renders a Table at md+ and a stacked card list below md,
 * from the SAME `rows` source (no duplicated markup).
 *
 * Props:
 *   columns: Array<{
 *     key: string,         — unique key (also used as header text if `header` omitted)
 *     header?: ReactNode,  — column header label
 *     cell: (row) => ReactNode, — cell renderer
 *     className?: string,  — extra class on the <th>/<td>
 *     mobileLabel?: string, — shown above value in card layout (defaults to header)
 *     hideOnMobile?: boolean — skip this field in the card layout
 *   }>
 *   rows: Array<any>      — data rows
 *   getRowKey: (row) => string | number — unique key per row
 *   renderCard?: (row) => ReactNode — optional fully-custom card override
 *   emptyText?: string — shown when rows is empty
 *   className?: string — extra class on wrapper
 *   tableClassName?: string
 *   onRowClick?: (row) => void — optional row click handler (table only)
 */
function DataList({
  columns = [],
  rows = [],
  getRowKey,
  renderCard,
  emptyText = "No items.",
  className,
  tableClassName,
  onRowClick,
}) {
  if (rows.length === 0) {
    return (
      <div
        data-slot="data-list-empty"
        className={cn(
          "rounded-xl border px-6 py-10 text-center text-sm text-muted-foreground",
          className
        )}
      >
        {emptyText}
      </div>
    )
  }

  return (
    <div data-slot="data-list" className={cn("w-full", className)}>
      {/* ── Table (md+) ── */}
      <div className={cn("hidden md:block rounded-xl border", tableClassName)}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col.key} className={col.className}>
                  {col.header ?? col.key}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={getRowKey ? getRowKey(row) : row.id}
                className={cn(onRowClick && "cursor-pointer")}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((col) => (
                  <TableCell key={col.key} className={col.className}>
                    {col.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* ── Card list (<md) ── */}
      <div className="flex flex-col gap-3 md:hidden">
        {rows.map((row) => {
          const key = getRowKey ? getRowKey(row) : row.id
          if (renderCard) {
            return <div key={key}>{renderCard(row)}</div>
          }
          return (
            <div
              key={key}
              role={onRowClick ? "button" : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              className={cn(
                "rounded-xl border bg-card px-4 py-3 shadow-sm",
                onRowClick && "cursor-pointer hover:bg-muted/50 transition-colors"
              )}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={onRowClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(row) } } : undefined}
            >
              {columns
                .filter((col) => !col.hideOnMobile)
                .map((col) => {
                  const label = col.mobileLabel ?? (typeof col.header === "string" ? col.header : col.key)
                  return (
                    <div key={col.key} className="flex items-baseline justify-between gap-2 py-0.5">
                      {label && (
                        <span className="text-xs text-muted-foreground shrink-0">{label}</span>
                      )}
                      <span className="text-sm text-right">{col.cell(row)}</span>
                    </div>
                  )
                })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export { DataList }
