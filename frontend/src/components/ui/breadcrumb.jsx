import { Link } from "react-router-dom"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Breadcrumb — renders a trail of links.
 *
 * items: Array<{ label: string, to?: string }>
 *   - items without `to` are rendered as plain text (current page).
 *   - the last item automatically gets aria-current="page".
 *
 * Example:
 *   <Breadcrumb items={[
 *     { label: "Classes", to: "/classes" },
 *     { label: "Grade 8A", to: "/classes/42" },
 *     { label: "Analytics" },
 *   ]} />
 */
function Breadcrumb({ items = [], className, ...props }) {
  return (
    <nav
      aria-label="Breadcrumb"
      data-slot="breadcrumb"
      className={cn("flex items-center gap-1 text-sm text-muted-foreground", className)}
      {...props}
    >
      <ol className="flex items-center gap-1 flex-wrap">
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1
          return (
            <li key={idx} className="flex items-center gap-1">
              {idx > 0 && (
                <ChevronRight
                  className="size-3.5 shrink-0 text-muted-foreground/60"
                  aria-hidden="true"
                />
              )}
              {item.to && !isLast ? (
                <Link
                  to={item.to}
                  className="hover:text-foreground hover:underline transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  aria-current={isLast ? "page" : undefined}
                  className={cn(isLast && "text-foreground font-medium")}
                >
                  {item.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export { Breadcrumb }
