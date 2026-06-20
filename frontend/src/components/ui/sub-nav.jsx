import { cn } from "@/lib/utils"

/**
 * SubNav — a Supabase-style in-page sub-sidebar. A vertical list of section
 * links on the left (horizontal scroll on mobile) that switches the section
 * shown on the right, instead of stacking every section on one long page.
 *
 * Drive it with state:  const [tab, setTab] = useState("general")
 */
export function SubNav({ sections, value, onChange, className }) {
  return (
    <nav
      aria-label="Section navigation"
      className={cn(
        "flex gap-1 overflow-x-auto pb-1 sm:w-56 sm:shrink-0 sm:flex-col sm:overflow-visible sm:pb-0",
        className,
      )}
    >
      {sections.map((s) => (
        <button
          key={s.key}
          type="button"
          onClick={() => onChange(s.key)}
          aria-current={value === s.key ? "page" : undefined}
          className={cn(
            "flex min-h-[40px] shrink-0 items-center whitespace-nowrap rounded-md px-3 py-2 text-left text-sm font-medium motion-safe-card outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
            value === s.key
              ? "bg-nav-active-bg text-nav-active-fg"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          {s.label}
        </button>
      ))}
    </nav>
  )
}

/** SubNav + a content column, in the standard two-column page layout. */
export function SubNavLayout({ sections, value, onChange, children }) {
  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:gap-8">
      <SubNav sections={sections} value={value} onChange={onChange} />
      <div className="min-w-0 flex-1 space-y-6">{children}</div>
    </div>
  )
}
